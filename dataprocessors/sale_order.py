# -*- coding: utf-8 -*-

"""
Created on october 2019

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

        sale_order_model = odooenv["sale.order"]
        # sale_order_line_model = odooenv["sale.order.line"]
        res_partner_model = odooenv["res.partner"]
        acc_payterm_model = odooenv["account.payment.term"]
        sale_order_model = odooenv["sale.order"]
        # sale_order_line_model = odooenv["sale.order.line"]
        res_partner_model = odooenv["res.partner"]
        acc_payterm_model = odooenv["account.payment.term"]

        dolicursor = dolidb.cursor()

        dolicursor.execute(
            """ SELECT c.rowid, c.ref, c.ref_client, c.date_creation,c.date_valid, c.date_cloture,
                         s.nom, t.libelle
                                FROM llx_societe s, llx_commande c
                                LEFT OUTER JOIN llx_c_payment_term t
                                    on c.fk_cond_reglement = t.rowid
                                WHERE c.fk_soc=s.rowid;"""
        )

        # Process sale.order
        for (
            cmd_id,
            cmdnum,
            ref_client,
            date_crea,
            date_valid,
            date_cloture,
            soc_nom,
            cond_pai,
        ) in dolicursor.fetchall():
            cmd = None

            found = sale_order_model.search([("name", "=", cmdnum)])

            p_found = res_partner_model.search([("name", "=", soc_nom)])

            if cond_pai:
                cond_pai_found = acc_payterm_model.search([("name", "=", cond_pai)])
            else:
                cond_pai_found = []

            if len(p_found) == 1:
                values = {
                    "name": cmdnum,
                    "partner_id": p_found[0].id,
                    "validity_date": toString(date_valid),
                    "client_order_ref": ref_client,
                    "state": "draft",
                }

                if len(cond_pai_found) == 1:
                    values["payment_term_id"] = cond_pai_found[0].id

                if len(found) == 1 and len(p_found) == 1:
                    cmd = found[0]
                    cmd.write(values)
                elif len(found) == 0 and len(p_found) == 1:
                    cmd = sale_order_model.create(values)
                else:
                    logger.warn(
                        "WARNING: several account_invoice found for name = %s", cmdnum
                    )
            else:
                logger.exception("Partner not found for: %s [processing %s]", soc_nom, cmdnum)

        dolicursor.close()
    except mysql.connector.Error as err:
        logger.exception("SQL Error: %s", str(err))
        return -1
