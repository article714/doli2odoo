# -*- coding: utf-8 -*-

'''
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2017 Article714
@license: AGPL
'''


def update_payment_terms (logger, odooenv, odoocr, dolidb):
    #******************************************************************
    # Iteration sur les conditions de paiement

    logger.info("Migration des conditions de paiement \n")

    acc_payterm_model = odooenv['account.payment.term']
    # acc_paytermline_model = odooenv['account.payment.term.line']

    dolicursor = dolidb.cursor()
    dolicursor.execute("SELECT libelle,libelle_facture,fdm,nbjour FROM llx_c_payment_term;")

    for (libelle, libelle_facture, fdm, nbjour) in dolicursor.fetchall():
        found = acc_payterm_model.search([('name', '=', libelle)])
        values = { 'name':libelle, 'note':libelle_facture}
        if len(found) == 1:
            acc_pt = found[0]
        else:
            acc_pt = acc_payterm_model.create(values)

        odoocr.commit()

        # conditions
        acc_pt_line = acc_pt.line_ids[0]
        if fdm == 1:
            if nbjour > 30:
                acc_pt_line.write({'value':'balance', 'option':'last_day_following_month'})
            else:
                acc_pt_line.write({'value':'balance', 'option':'last_day_current_month'})
        else:
            acc_pt_line.write({'value':'balance', 'option':'day_after_invoice_date', 'days':nbjour})

    dolicursor.close()
    found = None
