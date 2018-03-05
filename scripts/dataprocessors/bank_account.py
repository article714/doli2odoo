# -*- coding: utf-8 -*-

'''
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
'''

from odootools.Converters import toString


def process (logger, odooenv, odoocr, dolidb):
    #******************************************************************
    # Itération sur les banques et comptes bancaires

    logger.info("Migration des comptes bancaires \n")

    res_bank_model = odooenv['res.bank']
    account_journal_model = odooenv['account.journal']
    account_account_model = odooenv['account.account']
    account_account_type_model = odooenv['account.account.type']

    nestedquery = "select distinct iban_prefix,label,account_number FROM llx_bank_account where bank=%s;"

    # looking for bank account type

    found = account_account_type_model.search(['|', ('name', 'ilike', '%bank%'), ('name', 'ilike', '%banq%')], limit = 1)
    if len(found) == 1:
        bank_account_type_id = found[0].id

    # loop over bank accounts to find banks

    dolicursor = dolidb.cursor()
    dolicursor.execute("select distinct bank, bic FROM llx_bank_account;")

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

            for (iban, label, account_number) in dolipcursor.fetchall():
                iban = toString(iban).replace(' ', '').strip()

                # Account
                found = account_account_model.search([('code', '=', account_number)])

                values = {'user_type_id':bank_account_type_id, 'code':account_number,
                          'name':label}

                if len(found) == 1:
                    the_account = found[0]
                    the_account.write(values)
                else:
                    the_account = account_account_model.create(values)

                # Journal

                found = account_journal_model.search(['|', ('bank_acc_number', '=', iban), ('name', '=', label)])
                values = {'type':'bank',
                          'name':label,
                         'bank_id': a_bank.id}
                if iban != None and len(iban) > 2:
                    values['bank_acc_number'] = iban
                if the_account != None:
                    values['default_debit_account_id'] = the_account.id
                    values['default_credit_account_id'] = the_account.id

                if len(found) == 1:
                    the_journal = found[0]
                    the_journal.write(values)
                else:
                    the_journal = account_journal_model.create(values)

            odoocr.commit()
            dolipcursor.close()

    dolicursor.close()
