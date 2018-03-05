# -*- coding: utf-8 -*-

'''
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2017 Article714
@license: AGPL
'''

from odootools.Converters import toString


def update_bank_accounts (logger, odooenv, odoocr, dolidb):
    #******************************************************************
    # Itération sur les banques et comptes bancaires

    logger.info("Migration des relevés bancaires \n")

    res_bank_model = odooenv['res.bank']
    account_journal_model = odooenv['account.journal']

    dolicursor = dolidb.cursor()
    dolicursor.execute(""" select distinct DATE_FORMAT(STR_TO_DATE(CONCAT(b.num_releve,'01'),'%Y%m%d'),'%M %Y') as reldate, b.num_releve, a.iban_prefix,a.rowid as acc_id from llx_bank b, llx_bank_account a
                        where a.rowid = b.fk_account and num_releve like '20%' and iban_prefix like '%1106'
                        ;""")

    nestedquery = "select * FROM llx_bank where fk_account=%s;"

    for (reldate, num_releve, iban_prefix, acc_id) in dolicursor.fetchall():

        iban_prefix = iban_prefix.replace(' ', '')
        found = account_journal_model.search([('bank_acc_number', '=', iban_prefix)])
        a_bank = None
        if len(found) == 1:
            a_bank = found[0]

        # Comptes bancaires
        if a_bank:
            dolipcursor = dolidb.cursor()
            dolipcursor.execute(nestedquery, (acc_id,))

            for (ecriture,) in dolipcursor.fetchall():
                print ("TODO")

            odoocr.commit()
            dolipcursor.close()

    dolicursor.close()
