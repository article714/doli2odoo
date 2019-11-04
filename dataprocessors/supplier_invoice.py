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

depends = ["payment_term", "purchase_order"]


def process(logger, odooenv, odoocr, dolidb):
    """
    Do the Job for supplier invoices
    """
    try:

        account_invoice_model = odooenv["account.invoice"]
        account_invoice_line_model = odooenv["account.invoice.line"]
        account_invoice_tax_model = odooenv["account.invoice.tax"]
        account_tax_group_model = odooenv["account.tax.group"]
        res_partner_model = odooenv["res.partner"]
        acc_payterm_model = odooenv["account.payment.term"]
        product_template_model = odooenv["product.template"]
        account_journal_model = odooenv["account.journal"]

        # ******************************************************************
        # Default product used to import supplier invoice, when product not found

        default_product = product_template_model.search(
            [("default_code", "=", "GEN-SERV")]
        )

        # ******************************************************************
        # recherche des taxes à l'achat

        tvas = odooenv["account.tax"].search(
            [("description", "=", u"TVA 20%"), ("type_tax_use", "=", "purchase")]
        )
        tva_20 = tvas[0]
        tvas = odooenv["account.tax"].search(
            [("description", "=", u"TVA 10%"), ("type_tax_use", "=", "purchase")]
        )
        tva_10 = tvas[0]
        tvas = odooenv["account.tax"].search(
            [("description", "=", u"TVA 5,5%"), ("type_tax_use", "=", "purchase")]
        )
        tva_55 = tvas[0]
        tvas = odooenv["account.tax"].search(
            [("description", "=", u"TVA 2,1%"), ("type_tax_use", "=", "purchase")]
        )
        tva_21 = tvas[0]
        tvas = odooenv["account.tax"].search(
            [
                ("description", "=", u"TVA 19,6%"),
                ("active", "=", False),
                ("type_tax_use", "=", "purchase"),
            ]
        )
        if len(tvas) != 1:
            tva_196 = tva_20.copy()
            gpe = account_tax_group_model.search([("name", "=", "TVA 19,6%")])
            if len(gpe) == 0:
                gpe = account_tax_group_model.create({"name": "TVA 19,6%"})
            tva_196.write(
                {
                    "name": u"TVA déductible (achat) 19,6%",
                    "amount": 19.6000,
                    "description": "TVA 19,6%",
                    "active": False,
                    "type_tax_use": "purchase",
                    "tax_group_id": gpe.id,
                    "tag_ids": (5, False, False),
                }
            )
        else:
            tva_196 = tvas[0]
        tvas = odooenv["account.tax"].search(
            [
                ("description", "=", u"TVA 7,0%"),
                ("active", "=", False),
                ("type_tax_use", "=", "purchase"),
            ]
        )
        if len(tvas) != 1:
            tva_70 = tva_20.copy()
            gpe = account_tax_group_model.search([("name", "=", "TVA 7,0%")])
            if len(gpe) == 0:
                gpe = account_tax_group_model.create({"name": "TVA 7,0%"})
            tva_70.write(
                {
                    "name": u"TVA déductible (achat) 7,0%",
                    "amount": 7.000,
                    "description": "TVA 7,0%",
                    "active": False,
                    "type_tax_use": "purchase",
                    "tax_group_id": gpe.id,
                    "tag_ids": (5, False, False),
                }
            )
        else:
            tva_70 = tvas[0]

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
            """SELECT f.rowid,f.facnumber, f.ref_ext, f.datec,s.nom , t.libelle
                             FROM llx_societe s, llx_facture_fourn f
                               LEFT OUTER JOIN llx_c_payment_term t on f.fk_cond_reglement = t.rowid
                             WHERE f.fk_soc=s.rowid ;"""
        )

        nestedquery = (
            "SELECT f.description,f.tva_tx,f.qty,f.pu_ht, p.ref "
            "FROM llx_facture_fourn_det f"
            " LEFT OUTER JOIN llx_product p ON f.fk_product = p.rowid"
            " where f.fk_facture_fourn=%s"
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
            fact = None

            found = account_invoice_model.search([("name", "=", facnum)])
            p_found = res_partner_model.search([("name", "=", soc_nom)])

            if cond_pai:
                cond_pai_found = acc_payterm_model.search([("name", "=", cond_pai)])
            else:
                cond_pai_found = []

            if len(p_found) == 1:
                values = {
                    "reference": facnum,
                    "partner_id": p_found[0].id,
                    "date_invoice": toString(date_crea),
                    "reference": facnum,
                    "state": "draft",
                    "type": "in_invoice",
                    "journal_id": journal_fournisseur.id
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
                tax_lines = {}
                dolipcursor = dolidb.cursor()
                dolipcursor.execute(nestedquery, (fac_id,))

                if dolipcursor:
                    for (
                        description,
                        tva_tx,
                        qty,
                        subprice,
                        p_ref,
                    ) in dolipcursor:
                        lf_found = account_invoice_line_model.search(
                            [
                                ("invoice_id", "=", fact.id),
                                ("name", "=", description),
                                ("price_unit", "=", subprice),
                            ]
                        )
                        nb_lf = len(lf_found)
                        if nb_lf < 2:
                            p_id = default_product.id
                            acc_id = default_product.property_account_expense_id.id
                            if p_ref is not None:
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
                                if tva_196.id not in tax_lines:
                                    line = account_invoice_tax_model.search(
                                        [
                                            ("invoice_id", "=", fact.id),
                                            ("name", "=", tva_196.name),
                                        ]
                                    )
                                    if len(line) == 0:
                                        tax_lines[
                                            tva_196.id
                                        ] = account_invoice_tax_model.create(
                                            {
                                                "account_id": tva_196.account_id.id,
                                                "invoice_id": fact.id,
                                                "name": tva_196.name,
                                                "manual": False,
                                            }
                                        )
                                    else:
                                        tax_lines[tva_196.id] = line[0]
                            elif tva_tx == 10:
                                taxes = [(6, False, (tva_10.id,))]
                                if tva_10.id not in tax_lines:
                                    line = account_invoice_tax_model.search(
                                        [
                                            ("invoice_id", "=", fact.id),
                                            ("name", "=", tva_10.name),
                                        ]
                                    )
                                    if len(line) == 0:
                                        tax_lines[
                                            tva_10.id
                                        ] = account_invoice_tax_model.create(
                                            {
                                                "account_id": tva_10.account_id.id,
                                                "invoice_id": fact.id,
                                                "name": tva_10.name,
                                                "manual": False,
                                            }
                                        )
                                    else:
                                        tax_lines[tva_10.id] = line[0]
                            elif tva_tx == 7:
                                taxes = [(6, False, (tva_70.id,))]
                                if tva_70.id not in tax_lines:
                                    line = account_invoice_tax_model.search(
                                        [
                                            ("invoice_id", "=", fact.id),
                                            ("name", "=", tva_70.name),
                                        ]
                                    )
                                    if len(line) == 0:
                                        tax_lines[
                                            tva_70.id
                                        ] = account_invoice_tax_model.create(
                                            {
                                                "account_id": tva_70.account_id.id,
                                                "invoice_id": fact.id,
                                                "name": tva_70.name,
                                                "manual": False,
                                            }
                                        )
                                    else:
                                        tax_lines[tva_70.id] = line[0]
                            elif tva_tx == 5.5:
                                taxes = [(6, False, (tva_55.id,))]
                                if tva_55.id not in tax_lines:
                                    line = account_invoice_tax_model.search(
                                        [
                                            ("invoice_id", "=", fact.id),
                                            ("name", "=", tva_55.name),
                                        ]
                                    )
                                    if len(line) == 0:
                                        tax_lines[
                                            tva_55.id
                                        ] = account_invoice_tax_model.create(
                                            {
                                                "account_id": tva_55.account_id.id,
                                                "invoice_id": fact.id,
                                                "name": tva_55.name,
                                                "manual": False,
                                            }
                                        )
                                    else:
                                        tax_lines[tva_55.id] = line[0]
                            elif tva_tx == 2.1:
                                taxes = [(6, False, (tva_21.id,))]
                                if tva_21.id not in tax_lines:
                                    line = account_invoice_tax_model.search(
                                        [
                                            ("invoice_id", "=", fact.id),
                                            ("name", "=", tva_21.name),
                                        ]
                                    )
                                    if len(line) == 0:
                                        tax_lines[
                                            tva_21.id
                                        ] = account_invoice_tax_model.create(
                                            {
                                                "account_id": tva_21.account_id.id,
                                                "invoice_id": fact.id,
                                                "name": tva_21.name,
                                                "manual": False,
                                            }
                                        )
                                    else:
                                        tax_lines[tva_21.id] = line[0]
                            elif tva_tx == 0:
                                taxes = [(5, False, False)]
                            else:
                                taxes = [(6, False, (tva_20.id,))]
                                if tva_20.id not in tax_lines:
                                    line = account_invoice_tax_model.search(
                                        [
                                            ("invoice_id", "=", fact.id),
                                            ("name", "=", tva_20.name),
                                        ]
                                    )
                                    if len(line) == 0:
                                        tax_lines[
                                            tva_20.id
                                        ] = account_invoice_tax_model.create(
                                            {
                                                "account_id": tva_20.account_id.id,
                                                "invoice_id": fact.id,
                                                "name": tva_20.name,
                                                "manual": False,
                                            }
                                        )
                                    else:
                                        tax_lines[tva_20.id] = line[0]
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
                    if fact:
                        fact.compute_taxes()
                        fact._compute_amount()

                    dolipcursor.close()

            odoocr.commit()

        dolicursor.close()
    except mysql.connector.Error as err:
        logger.exception("SQL Error: " + str(err))
        return -1
