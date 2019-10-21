# -*- coding: utf-8 -*-

"""
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
"""

import mysql.connector

from odootools.Converters import toString

# dataprocessors we depend on

depends = ["product", "payment_term"]


def process(logger, odooenv, odoocr, dolidb):
    """
    Do the job of updating a customer invoice
    """
    try:

        # ******************************************************************
        # Itération sur les devis & factures (clients)

        # sale_order_model = odooenv["sale.order"]
        # sale_order_line_model = odooenv["sale.order.line"]
        account_journal_model = odooenv["account.journal"]
        res_partner_model = odooenv["res.partner"]
        acc_payterm_model = odooenv["account.payment.term"]
        product_template_model = odooenv["product.template"]
        account_tax_group_model = odooenv["account.tax.group"]

        # ******************************************************************
        # recherche des taxes à la vente

        tvas = odooenv["account.tax"].search(
            [("name", "=", u"TVA collectée (vente) 20,0%")]
        )
        tva_20 = tvas[0]
        tvas = odooenv["account.tax"].search(
            [
                ("description", "=", "TVA 19,6%"),
                ("active", "=", False),
                ("type_tax_use", "=", "sale"),
            ]
        )
        if len(tvas) != 1:
            gpe = account_tax_group_model.search([("name", "=", "TVA 19,6%")])
            if len(gpe) == 0:
                gpe = account_tax_group_model.create({"name": "TVA 19,6%"})
            tva_196 = tva_20.copy()
            tva_196.write(
                {
                    "name": u"TVA collectée (vente) 19,6%",
                    "amount": 19.6000,
                    "description": "TVA 19,6%",
                    "type_tax_use": "sale",
                    "tax_group_id": gpe.id,
                    "active": False,
                    "tag_ids": (5, False, False),
                }
            )
        else:
            tva_196 = tvas[0]

        odoocr.commit()

        # recherche du journal client
        journal_client = None
        found = account_journal_model.search([("code", "=", "FAC")])
        if len(found) == 1:
            journal_client = found[0]
        else:
            logger.error("Impossible de trouver le journal de facturation")

        logger.info("Migration des devis/commandes clients \n")

        dolicursor = dolidb.cursor()
        dolicursor.execute(
            """ SELECT f.rowid, f.facnumber,f.datec,f.date_valid,s.nom, t.libelle
                               FROM llx_societe s, llx_facture f
                               LEFT OUTER JOIN llx_c_payment_term t on f.fk_cond_reglement = t.rowid
                               WHERE f.fk_soc=s.rowid;"""
        )

        nestedquery = (
            "SELECT f.label,f.description,f.tva_tx,f.qty,f.subprice, p.ref FROM llx_facturedet f"
            + " LEFT OUTER JOIN llx_product p ON f.fk_product = p.rowid where f.fk_facture=%s"
        )

        for (
            fac_id,
            facnum,
            date_crea,
            date_valid,
            soc_nom,
            cond_pai,
        ) in dolicursor.fetchall():

            sale_order = None
            fact = None

            p_found = res_partner_model.search([("name", "=", soc_nom)])

            # no saleorders for now
            # found = sale_order_model.search([("name", "=", cmdnum)])
            
            if cond_pai:
               cond_pai_found = acc_payterm_model.search([("name", "=", cond_pai)])
            else:
               cond_pai_found = []
            
            if len(p_found) == 1:
                values = {
                    "name": cmdnum,
                    "partner_id": p_found[0].id,
                    "date_order": toString(date_crea),
                    "confirmation_date": toString(date_valid),
                    "state": "sale",
                    "user_id": None,
                }

                if len(cond_pai_found) == 1:
                    values["payment_term_id"] = cond_pai_found[0].id

                if len(found) == 1:
                    sale_order = found[0]
                    sale_order.write(values)

                elif len(found) == 0:
                    sale_order = sale_order_model.create(values)
                else:
                    logger.warn(
                        "WARNING: several sale_order found for name = " + facnum
                    )
            else:
                logger.warn("WARNING: found no partner for sale.order = " + facnum)

            if sale_order != None:
                dolipcursor = dolidb.cursor()
                dolipcursor.execute(nestedquery, (fac_id,))

                if dolipcursor:
                    for (
                        label,
                        description,
                        tva_tx,
                        qty,
                        subprice,
                        p_ref,
                    ) in dolipcursor:
                        ol_found = sale_order_line_model.search(
                            [
                                "&",
                                ("order_id", "=", sale_order.id),
                                ("name", "=", description),
                            ]
                        )
                        nb_ol = len(ol_found)
                        if nb_ol < 2:
                            p_id = default_product.id
                            if p_ref != None:
                                prod_found = product_template_model.search(
                                    [("default_code", "=", p_ref)]
                                )
                                if len(prod_found) == 1:
                                    p_id = prod_found[0].id
                            if tva_tx == 19.600:
                                taxes = [(6, False, (tva_196.id,))]
                            elif tva_tx == 0:
                                taxes = [(5, False, False)]
                            else:
                                taxes = [(6, False, (tva_20.id,))]
                            values = {
                                "order_id": sale_order.id,
                                "product_id": p_id,
                                "product_uom_qty": qty,
                                "customer_lead": 0,
                                "price_unit": subprice,
                                "name": description,
                                "tax_id": taxes,
                            }
                        if nb_ol == 1:
                            ol = ol_found[0]
                            ol.write(values)
                        elif nb_ol == 0:
                            ol = sale_order_line_model.create(values)
                        else:
                            logger.warn(
                                "WARNING: several sale_order_line found for name = "
                                + description
                            )

                    dolipcursor.close()
                    odoocr.commit()

            odoocr.commit()

            # génération de la facture qui va avec

            if sale_order != None:
                if len(sale_order.invoice_ids) == 0:
                    sale_order.action_invoice_create(final=True, grouped=True)
                fact = sale_order.invoice_ids[0]

                values = {
                    "name": facnum,
                    "number": facnum,
                    "date_invoice": toString(date_crea),
                    "journal_id": journal_client.id,
                }

                if len(cond_pai_found) == 1:
                    values["payment_term_id"] = cond_pai_found[0].id

                fact.write(values)

                if fact.state == "draft":
                    # recalcul de la date d'échéance
                    fact._onchange_payment_term_date_invoice()

                    # passage en "ouvert" avec génération des écritures comptables
                    fact.action_move_create()
                    fact.state = "open"
                    fact.write({"state": "open", "number": facnum})
                    odoocr.commit()

                odoocr.commit()

        dolicursor.close()

    except mysql.connector.Error as err:
        logger.error("SQL Error: " + str(err))
        return -1
