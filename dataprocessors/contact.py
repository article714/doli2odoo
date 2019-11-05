# -*- coding: utf-8 -*-

"""
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
"""

import mysql.connector

from odoo.exceptions import ValidationError
from odootools.Converters import toString


def process(logger, odooenv, odoocr, dolidb):

    try:

        # ******************************************************************
        # Country map cash

        countries = {}

        found_countries = odooenv["res.country"].search([("code", "=", "FR")], limit=1)
        if len(found_countries) == 1:
            countries["FR"] = found_countries[0].id

        # ******************************************************************
        # Itération sur les sociétés

        res_partner_model = odooenv["res.partner"]
        res_part_categ_model = odooenv["res.partner.category"]

        logger.info("Migration des societes et contacts \n")

        nestedquery = (
            "select name,firstname,poste,email from llx_socpeople where fk_soc=%s"
        )

        dolicursor = dolidb.cursor()
        dolicursor.execute(
            """
            select s.rowid,s.nom,s.address,s.cp,s.ville,s.tel,s.fax,s.url,s.email,s.client,
            s.fournisseur,s.siret,s.ape,s.tva_intra,s.tms,p.code
            from llx_societe s, llx_c_pays p where s.fk_pays=p.rowid
            """
        )

        for (
            soc_id,
            name,
            addr,
            azip,
            city,
            phone,
            fax,
            url,
            email,
            is_client,
            is_fournisseur,
            siret,
            ape,
            tva_intra,
            last_update,
            code_iso,
        ) in dolicursor.fetchall():

            # country search
            if code_iso not in countries:
                found_countries = odooenv["res.country"].search(
                    [("code", "=", code_iso)], limit=1
                )
                if len(found_countries) == 1:
                    countries[code_iso] = found_countries[0].id

            found_partners = res_partner_model.search([("name", "=", name)])
            is_customer = (is_client == 1) or (is_client == 3)
            is_supplier = is_fournisseur > 0
            values = {
                "name": name,
                "street": addr,
                "zip": azip,
                "city": city,
                "phone": phone,
                "fax": fax,
                "website": url,
                "email": email,
                "company_type": "company",
                "is_company": True,
                "customer": is_customer,
                "supplier": is_supplier,
                "country_id": countries[code_iso],
            }

            if ape:
                naf = "%s.%s"%(ape[0:2],ape[2:])
                naf = naf.upper()
                found = res_part_categ_model.search([("name", "like", "%" + naf + "%")])
                if len(found) == 1:
                    values["ape_id"] = found[0].id

            try:
                if len(found_partners) == 1:
                    partner = found_partners[0]
                    partner.write(values)
                elif len(found_partners) == 0:
                    partner = res_partner_model.create(values)
                else:
                    logger.warn("WARNING: several res.partner found for name = %s", name)

            except ValidationError as e:
                logger.error("Data Error : %s", str(e))

            odoocr.commit()
            # ******************************************************************
            # Itération sur les personnes

            dolipcursor = dolidb.cursor()

            dolipcursor.execute(nestedquery, (soc_id,))

            if dolipcursor:
                for (plname, pfname, poste, email) in dolipcursor:
                    ctct_name = "%s %s" % (pfname, plname)
                    ctct_name_2 = "%s %s" % (plname, pfname)
                    found = res_partner_model.search(
                        ["&", ("name", "=", ctct_name), ("parent_id", "=", partner.id)]
                    )
                    found2 = res_partner_model.search(
                        [
                            "&",
                            ("name", "=", ctct_name_2),
                            ("parent_id", "=", partner.id),
                        ]
                    )

                    values = {
                        "name": ctct_name,
                        "parent_id": partner.id,
                        "function": poste,
                        "email": email,
                        "company_type": "person",
                        "is_company": False,
                        "country_id": countries[code_iso],
                    }
                    try:
                        if len(found) == 1:
                            contact = found[0]
                            contact.write(values)
                        elif len(found2) == 1:
                            contact = found2[0]
                            contact.write(values)

                        elif len(found) == 0 and len(found2) == 0:
                            contact = res_partner_model.create(values)
                        else:
                            logger.warn(
                                "WARNING: several res.partner found for name = "
                                + ctct_name
                            )
                    except ValidationError as e:
                        logger.error("Data Error : %s", str(e))

                dolipcursor.close()
                odoocr.commit()
        dolicursor.close()
        return 0

    except mysql.connector.Error as err:
        logger.exception("SQL Error: %s", str(err))
        return -1
