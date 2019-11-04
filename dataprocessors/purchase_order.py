# -*- coding: utf-8 -*-

"""
Created on november 2019

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
"""

import mysql.connector

from odootools.Converters import toString

# dataprocessors we depend on

depends = ["contact", "product", "payment_term"]


def process(logger, odooenv, odoocr, dolidb):
    """
    Do the Job for customer sale orders
    """
    try:

        purchase_order_model = odooenv["purchase.order"]
        # sale_order_line_model = odooenv["sale.order.line"]
        res_partner_model = odooenv["res.partner"]
        acc_payterm_model = odooenv["account.payment.term"]

        dolicursor = dolidb.cursor()

        dolicursor.execute(
            """ SELECT c.rowid, c.ref, c.ref_supplier, c.ref_ext, c.date_creation,c.date_valid, c.date_cloture,
                        s.nom, t.libelle
                               FROM llx_societe s, llx_commande_fournisseur c
                               LEFT OUTER JOIN llx_c_payment_term t on c.fk_cond_reglement = t.rowid
                               WHERE c.fk_soc=s.rowid;"""
        )

        # Process purchase.order
        for (
            cmd_id,
            cmdnum,
            ref,
            ref_supplier,
            ref_ext,
            date_crea,
            date_valid,
            date_cloture,
            soc_nom,
            cond_pai,
        ) in dolicursor.fetchall():
            cmd = None

            found = purchase_order_model.search([("name", "=", cmdnum)])

            p_found = res_partner_model.search([("name", "=", soc_nom)])

            if cond_pai:
                cond_pai_found = acc_payterm_model.search([("name", "=", cond_pai)])
            else:
                cond_pai_found = []

            if len(p_found) == 1:
                values = {
                    "name": cmdnum,
                    "partner_id": p_found[0].id,
                    "date_order": toString(date_valid),
                    "state": "draft",
                    "partner_ref": ref_supplier
                }

                if len(cond_pai_found) == 1:
                    values["payment_term_id"] = cond_pai_found[0].id

                if len(found) == 1 and len(p_found) == 1:
                    cmd = found[0]
                    cmd.write(values)
                elif len(found) == 0 and len(p_found) == 1:
                    cmd = purchase_order_model.create(values)
                else:
                    logger.warn(
                        "WARNING: several account_invoice found for name = " + cmdnum
                    )
            else:
                logger.error("Partner not found for: %s", soc_nom)

        dolicursor.close()
    except mysql.connector.Error as err:
        logger.exception("SQL Error: " + str(err))
        return -1
