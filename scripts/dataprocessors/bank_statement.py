# -*- coding: utf-8 -*-

'''
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
'''

from odoo.exceptions import ValidationError
from odootools.Converters import toString, dateToOdooString


def process (logger, odooenv, odoocr, dolidb):
    #******************************************************************
    # Iterate on bank accounts

    logger.info("Migrating bank statements \n")

    account_journal_model = odooenv['account.journal']
    statement_model = odooenv['account.bank.statement']
    statement_line_model = odooenv['account.bank.statement.line']

    dolicursor = dolidb.cursor()
    dolicursor.execute(""" select DATE_FORMAT(STR_TO_DATE(CONCAT(b.num_releve,'01'),'%Y%m%d'),'%M %Y') as reldate, max(datev) as enddate, b.num_releve, a.iban_prefix,a.rowid as acc_id
                        from llx_bank b, llx_bank_account a
                        where a.rowid = b.fk_account and num_releve is not null
                        group by b.num_releve, a.iban_prefix,a.rowid
                        order by enddate asc
                        ;""")

    nestedquery = "select * FROM llx_bank where fk_account=%s and num_releve=%s;"

    for (reldate, enddate, num_releve, iban_prefix, acc_id) in dolicursor.fetchall():

        iban_prefix = iban_prefix.replace(' ', '')
        found = account_journal_model.search([('bank_acc_number', '=', iban_prefix)])
        a_bank_journal = None
        if len(found) == 1:
            a_bank_journal = found[0]

        # Bank statement
        if a_bank_journal:

            # search bank_statement
            found = statement_model.search(['&', ('name', '=', str(num_releve) + '- ' + str(reldate)), ('journal_id', '=', a_bank_journal.id)], limit = 1)
            values = {'name':str(num_releve) + '- ' + str(reldate),
                      'journal_id': a_bank_journal.id,
                      'date':dateToOdooString(enddate)
                }
            try:
                if len(found) == 1:
                    the_statement = found[0]
                    the_statement.write(values)
                else:
                    the_statement = statement_model.create(values)

                odoocr.commit()
            except ValidationError as e:
                logger.error("Wrong Data : " + str(values))
                continue

            # Bank statement lines
            if the_statement != None:
                dolipcursor = dolidb.cursor()
                dolipcursor.execute(nestedquery, (acc_id, num_releve))

                # Records
                for ecriture in dolipcursor.fetchall():
                    imp_id = "D2Odoo-" + str(ecriture[0])
                    values = {'amount':ecriture[4],
                              'statement_id':the_statement.id,
                              'date': dateToOdooString(ecriture[2]),
                              'unique_import_id': imp_id,
                              'name': dateToOdooString(ecriture[5])
                                }

                    found = statement_line_model.search([('unique_import_id', '=', imp_id)], limit = 1)
                    try:
                        if len(found) == 1:
                            found[0].write(values)
                        else:
                            statement_line_model.create(values)
                    except Exception as e:
                        logger.warning("ERROR when updating/creating statement line: " + str(e))

            odoocr.commit()
            dolipcursor.close()

    dolicursor.close()
