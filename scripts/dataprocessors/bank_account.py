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

    logger.info("Migration des comptes bancaires \n")

    res_bank_model = odooenv['res.bank']
    account_journal_model = odooenv['account.journal']

    dolicursor = dolidb.cursor()
    dolicursor.execute("select distinct bank, bic FROM llx_bank_account;")

    nestedquery = "select distinct iban_prefix FROM llx_bank_account where bank=%s;"

    for (bank, bic) in dolicursor.fetchall():

        found = res_bank_model.search([('name', '=', bank)])

        values = {'name':bank, 'bic':bic}

        if len(found) == 1:
            a_bank = found[0]
            a_bank.write(values)
        else:
            a_bank = res_bank_model.create(values)

        odoocr.commit()

        # Comptes bancaires
        if a_bank:
            dolipcursor = dolidb.cursor()
            dolipcursor.execute(nestedquery, (bank,))

            for (iban,) in dolipcursor.fetchall():
                iban = toString(iban).replace(' ', '').strip()
                found = account_journal_model.search([('bank_acc_number', '=', iban)])

                values = {'type':'bank', 'bank_acc_number':iban,
                         'bank_id': a_bank.id}

                if len(found) == 1:
                    an_account = found[0]
                    an_account.write(values)
                else:
                    an_account = account_journal_model.create(values)

            odoocr.commit()
            dolipcursor.close()

    dolicursor.close()
