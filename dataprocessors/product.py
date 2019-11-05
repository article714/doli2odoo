# -*- coding: utf-8 -*-

"""
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
"""


def process(logger, odooenv, odoocr, dolidb):
    # ******************************************************************
    # Iteration sur les produits

    product_template_model = odooenv["product.template"]
    account_account_model = odooenv["account.account"]

    logger.info("Migrating producs \n")

    dolicursor = dolidb.cursor()
    dolicursor.execute(
        "select ref,label,description, price,tosell,tobuy from llx_product"
    )

    for (ref, label, description, price, tosell, tobuy) in dolicursor.fetchall():
        found = product_template_model.search([("default_code", "=", ref)])

        values = {
            "name": label,
            "default_code": ref,
            "type": "service",
            "list_price": price,
            "sale_ok": (tosell == 1),
            "purchase_ok": (tobuy == 1),
            "description_sale": description,
        }

        if len(found) == 1:
            prod = found[0]
            prod.write(values)
        elif len(found) == 0:
            prod = product_template_model.create(values)
        else:
            logger.warn(
                "WARNING: several product_template found for default_code = %s ", ref
            )

        odoocr.commit()

    dolicursor.close()

    # Produits Génériques

    found = product_template_model.search([("default_code", "=", "GEN-PREST")])
    values = {
        "name": "Prestation générique",
        "default_code": "GEN-PREST",
        "type": "service",
        "list_price": 600,
        "standard_price": 400,
        "sale_ok": True,
        "purchase_ok": False,
        "property_account_income_id": account_account_model.search(
            [("code", "=", "701100")]
        )[0].id,
    }
    if len(found) == 1:
        of_prest_prod = found[0]
        of_prest_prod.write(values)
    else:
        of_prest_prod = product_template_model.create(values)

    found = product_template_model.search([("default_code", "=", "GEN-SERV")])
    values = {
        "name": "Achat générique",
        "default_code": "GEN-SERV",
        "type": "service",
        "list_price": 0,
        "standard_price": 0,
        "sale_ok": False,
        "purchase_ok": True,
        "property_account_expense_id": account_account_model.search(
            [("code", "=", "601100")]
        )[0].id,
    }
    if len(found) == 1:
        ach_prest_gen = found[0]
        ach_prest_gen.write(values)
    else:
        ach_prest_gen = product_template_model.create(values)

    odoocr.commit()
