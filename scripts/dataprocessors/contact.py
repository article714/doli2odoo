# -*- coding: utf-8 -*-

'''
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2017 Article714
@license: AGPL
'''
from datetime import date, timedelta, datetime
import mysql.connector
import re

from odootools.Converters import toString


def update_partners(logger, odooenv, odoocr, dolidb):

    try:

        hier = datetime.combine(date.today() - timedelta(1), datetime.min.time())

        #******************************************************************
        # Récupération de l'id de France

        found_countries = odooenv['res.country'].search([('code', '=', 'FR')])

        fr_id = found_countries[0].id

        #******************************************************************
        # Itération sur les sociétés

        res_partner_model = odooenv['res.partner']
        res_part_categ_model = odooenv['res.partner.category']

        logger.info("Migration des societes et contacts \n")

        nestedquery = ("select lastname,firstname,poste,email from llx_socpeople where fk_soc=%s")

        dolicursor = dolidb.cursor()
        dolicursor.execute("select rowid,nom,address,zip,town,phone,fax,url,email,client,fournisseur,siret,ape,tva_intra,tms from llx_societe")

        for (soc_id, name, addr, azip, city, phone, fax, url, email, is_client, is_fournisseur, siret, ape, tva_intra, last_update) in dolicursor.fetchall():

            found_partners = res_partner_model.search([('name', '=', name)])
            is_customer = (is_client == 1) or (is_client == 3)
            is_supplier = (is_fournisseur > 0)
            values = {'name':name, 'street':addr, 'zip':azip, 'city':city,
                      'phone':phone, 'fax':fax, 'website':url, 'email':email,
                      'company_type':'company', 'is_company':True,
                      'customer':is_customer, 'supplier':is_supplier,
                      'notify_email':'none', 'country_id':fr_id
                      }
            if tva_intra:
                if re.match(r'[A-Z]{2}[0-9]{11}', tva_intra):
                    values['vat'] = tva_intra
                else:
                    logger.warning("TVA is not good: " + toString(tva_intra) + "-- " + name)

            if siret :
                if len(siret) == 14:
                    values['siren'] = siret[0:9]
                    values['nic'] = siret[9:]
                else:
                    logger.warning("SIRET is not good: " + toString(siret) + "-- " + name)

            if ape:
                naf = ape[0:2] + '.' + ape[2:]
                naf = naf.upper()
                found = res_part_categ_model.search([('name', 'like', '%' + naf + '%')])
                if len(found) == 1:
                    values['ape_id'] = found[0].id

            try:
                if len(found_partners) == 1:
                    partner = found_partners[0]
                    if last_update > hier:
                        partner.write(values)
                elif len(found_partners) == 0:
                    partner = res_partner_model.create(values)
                else:
                    logger.warn("WARNING: several res.partner found for name = " + name)

            except Exception as e:
                logger.error(toString(e))
                logger.error('Mauvaises valeurs pour le contact  ' + toString(name))

            odoocr.commit()
            #******************************************************************
            # Itération sur les personnes

            dolipcursor = dolidb.cursor()

            dolipcursor.execute(nestedquery, (soc_id,))

            if dolipcursor:
                for (plname, pfname, poste, email) in dolipcursor:
                    ctct_name = pfname + " " + plname
                    ctct_name_2 = plname + " " + pfname
                    found = res_partner_model.search(['&', ('name', '=', ctct_name), ('parent_id', '=', partner.id)])
                    found2 = res_partner_model.search(['&', ('name', '=', ctct_name_2), ('parent_id', '=', partner.id)])

                    values = {'name':ctct_name, 'parent_id':partner.id,
                              'function':poste, 'email':email,
                              'company_type':'person', 'is_company':False,
                              'notify_email':'none', 'country_id':fr_id}
                    if len(found) == 1:
                        contact = found[0]
                        contact.write(values)
                    elif len(found2) == 1:
                        contact = found2[0]
                        contact.write(values)

                    elif len(found) == 0 and len(found2) == 0:
                        contact = res_partner_model.create(values)
                    else:
                        logger.warn("WARNING: several res.partner found for name = " + ctct_name)

                dolipcursor.close()
                odoocr.commit()
        dolicursor.close()
        return 0

    except mysql.connector.Error as err:
        logger.error("SQL Error: " + str(err))
        return -1
