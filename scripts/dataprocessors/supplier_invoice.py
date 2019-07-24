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


def process(logger, odooenv, odoocr, dolidb):

    try:

        account_invoice_model = odooenv["account.invoice"]
        account_invoice_line_model = odooenv["account.invoice.line"]
        res_partner_model = odooenv["res.partner"]
        acc_payterm_model = odooenv["account.payment.term"]
        product_template_model = odooenv["product.template"]
        account_journal_model = odooenv["account.journal"]

        # ******************************************************************
        # Default product used to import supplier invoice, when product not found

        # TODO
        default_product = None

        # ******************************************************************
        # recherche des taxes à l'achat

        tvas = odooenv["account.tax"].search([("description", "=", u"ACH-20.0")])
        tva_20 = tvas[0]
        tvas = odooenv["account.tax"].search(
            ["&", ("description", "=", u"ACH-19.6"), ("active", "=", False)]
        )
        if len(tvas) != 1:
            tva_196 = tva_20.copy()
            tva_196.write(
                {
                    "name": u"TVA déductible (achat) 19,6%",
                    "amount": 19.6000,
                    "description": "ACH-19.6",
                    "active": False,
                    "tag_ids": (5, False, False),
                }
            )
        else:
            tva_196 = tvas[0]

        odoocr.commit()

        # ******************************************************************
        # Itération sur les devis & factures (fournisseurs)

        # recherche du journal fournisseur
        journal_fournisseur = None
        found = account_journal_model.search([("code", "=", "FACTU")])
        if len(found) == 1:
            journal_fournisseur = found[0]
        else:
            logger.error("Impossible de trouver le journal de facturation")

        # purchase_order_model = odooenv['purchase.order']

        dolicursor = dolidb.cursor()
        dolicursor.execute(
            """SELECT f.rowid,f.ref,f.ref_supplier,f.datec,s.nom , t.libelle
                             FROM llx_societe s, llx_facture_fourn f
                               LEFT OUTER JOIN llx_c_payment_term t on f.fk_cond_reglement = t.rowid
                             WHERE f.fk_soc=s.rowid ;"""
        )

        nestedquery = (
            "SELECT f.label,f.description,f.tva_tx,f.qty,f.pu_ht, p.ref FROM llx_facture_fourn_det f"
            + " LEFT OUTER JOIN llx_product p ON f.fk_product = p.rowid where f.fk_facture_fourn=%s"
        )

        logger.info("Migration des devis/commandes Fournisseurs \n")

        for (
            fac_id,
            facnum,
            ref_fourn,
            date_crea,
            soc_nom,
            cond_pai,
        ) in dolicursor.fetchall():
            facnum = str(facnum).replace("SI", "OF-FF-")
            fact = None

            found = account_invoice_model.search([("name", "=", facnum)])
            p_found = res_partner_model.search([("name", "=", soc_nom)])

            facnum = str(facnum).replace("SI", "OF-FF-")

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
                    "reference": ref_fourn,
                    "state": "draft",
                    "type": "in_invoice",
                    "journal_id": journal_fournisseur.id,
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

            if fact != None:
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
                            acc_id = default_product.property_account_expense_id.id
                            if p_ref != None:
                                prod_found = product_template_model.search(
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
        logger.error("SQL Error: " + str(err))
        return -1
