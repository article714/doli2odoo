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

depends = ["sale_order", "payment_term"]


def process(logger, odooenv, odoocr, dolidb):
    """
    Do the job of updating a customer invoice
    """
    try:

        # ******************************************************************
        # Itération sur les devis & factures (clients)

        account_invoice_model = odooenv["account.invoice"]
        account_invoice_line_model = odooenv["account.invoice.line"]
        # PAs de sale.order pour le moment
        # sale_order_model = odooenv["sale.order"]
        # sale_order_line_model = odooenv["sale.order.line"]
        account_journal_model = odooenv["account.journal"]
        res_partner_model = odooenv["res.partner"]
        acc_payterm_model = odooenv["account.payment.term"]
        product_product_model = odooenv["product.product"]
        account_tax_group_model = odooenv["account.tax.group"]

        # ******************************************************************
        # Default product used to import supplier invoice, when product not found

        default_product = product_product_model.search(
            [("default_code", "=", "GEN-PREST")]
        )

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
            """ SELECT f.rowid, f.facnumber,f.datec,f.date_valid,s.nom, f.ref_ext, f.ref_int,
                       f.ref_client, t.libelle, f.note, f.note_public
                               FROM llx_societe s, llx_facture f
                               LEFT OUTER JOIN llx_c_payment_term t on f.fk_cond_reglement = t.rowid
                               WHERE f.fk_soc=s.rowid;"""
        )

        nestedquery = """
            SELECT f.description,f.tva_tx,f.qty,f.subprice, p.ref FROM llx_facturedet f
            LEFT OUTER JOIN llx_product p ON f.fk_product = p.rowid where f.fk_facture=%s;
            """

        for (
            fac_id,
            facnum,
            date_crea,
            date_valid,
            soc_nom,
            ref_ext,
            ref_int,
            ref_client,
            cond_pai,
            note,
            note_public,
        ) in dolicursor.fetchall():
            fact = None

            found = account_invoice_model.search([("name", "=", facnum)])
            p_found = res_partner_model.search([("name", "=", soc_nom)])

            if cond_pai:
                cond_pai_found = acc_payterm_model.search([("name", "=", cond_pai)])
            else:
                cond_pai_found = []

            if len(p_found) == 1:
                values = {
                    "name": facnum,
                    "partner_id": p_found[0].id,
                    "number": facnum,
                    "date_invoice": toString(date_crea),
                    "reference": ref_client,
                    "state": "draft",
                    "type": "out_invoice",
                    "journal_id": journal_client.id,
                }

                if len(cond_pai_found) == 1:
                    values["payment_term_id"] = cond_pai_found[0].id

            if len(found) == 1 and len(p_found) == 1:
                fact = found[0]
                fact.write(values)
            elif len(found) == 0 and len(p_found) == 1:
                fact = account_invoice_model.create(values)
            else:
                logger.warn(
                    "WARNING: several account_invoice found for name = " + facnum
                )

            if fact is not None:
                dolipcursor = dolidb.cursor()
                dolipcursor.execute(nestedquery, (fac_id,))

                if dolipcursor:
                    for (description, tva_tx, qty, subprice, p_ref) in dolipcursor:
                        lf_found = account_invoice_line_model.search(
                            [
                                "&",
                                ("invoice_id", "=", fact.id),
                                ("name", "=", description),
                            ]
                        )
                        nb_lf = len(lf_found)
                        if nb_lf < 2:
                            p_id = default_product.id
                            acc_id = default_product.property_account_income_id.id
                            if p_ref is not None:
                                prod_found = product_product_model.search(
                                    [("default_code", "=", p_ref)]
                                )
                                if len(prod_found) == 1:
                                    p_id = prod_found[0].id
                                    if prod_found[0].property_account_expense_id:
                                        acc_id = (
                                            default_product.property_account_expense_id.id
                                        )
                            if tva_tx == 19.600:
                                taxes = [(6, False, (tva_196.id,))]
                            elif tva_tx == 0:
                                taxes = [(5, False, False)]
                            else:
                                taxes = [(6, False, (tva_20.id,))]
                            values = {
                                "invoice_id": fact.id,
                                "product_id": p_id,
                                "account_id": acc_id,
                                "quantity": qty,
                                "price_unit": subprice,
                                "name": description,
                                "invoice_line_tax_ids": taxes,
                            }
                        if nb_lf == 1:
                            lf = lf_found[0]
                            lf.write(values)
                        elif nb_lf == 0:
                            lf = account_invoice_line_model.create(values)
                        else:
                            logger.warn(
                                "WARNING: several account_invoice_line found for name = "
                                + description
                            )

                    dolipcursor.close()

            odoocr.commit()

        dolicursor.close()

    except mysql.connector.Error as err:
        logger.exception("SQL Error: " + str(err))
        return -1
