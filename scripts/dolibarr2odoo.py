#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2017 Article714
@license: AGPL
'''

import logging
import mysql.connector

from dataprocessors import contact, supplier_invoice, customer_invoice, bank_account
from odootools import OdooScript


#*************************************
# Mail Class
class dolibarr2Odoo(OdooScript.Script):

    # *************************************************************
    # overriden constructor

    def __init__(self):

        OdooScript.Script.__init__(self)

        self.processor = None

    #********************************************************************************
    # main script

    def run(self):

        # *************************************************************
        # connect to DolibarrDb
        try:
            dolidb = mysql.connector.connect(user = self.getConfigValue('dolibarr_user'),
                                          password = self.getConfigValue('dolibarr_pwd'),
                                          host = self.getConfigValue('dolibarr_host'),
                                          database = self.getConfigValue('dolibarr_db'))
        except mysql.connector.Error as err:
            self.logger.info(err)
            return -1

        #******************************************************************
        # Mise à jour des partenaires, contacts

        # De-activated -- > contact.update_partners(self.logger, self.env, self.cr, dolidb)

        #******************************************************************
        # Itération sur les produits

        # De-activated -- > product.update_products(self.logger, self.env, self.cr, dolidb)

        #******************************************************************
        # Itération sur les conditions de paiement

        # De-activated payment_term.update_payment_terms(self.logger, self.env, self.cr, dolidb)

        #******************************************************************
        # Itération sur les banques et comptes bancaires

        # De-activated bank_accounts.update_bank_accounts(self.logger, self.env, self.cr, dolidb)

        #******************************************************************
        # Mise à jour des commandes et factures client

        product_template_model = self.env['product.template']

        found = product_template_model.search([('default_code', '=', 'OF-PREST')])
        if len(found) == 1:
            of_prest_prod = found[0]
            customer_invoice.update_factures(of_prest_prod, self.logger, self.env, self.cr, dolidb)

        #******************************************************************
        # Mise à jour des commandes et factures client

        found = product_template_model.search([('default_code', '=', 'GEN-SERV')])
        if len(found) == 1:
            ach_prest_gen = found[0]
            supplier_invoice.update_factures(ach_prest_gen, self.logger, self.env, self.cr, dolidb)

        #******************************************************************
        # Fin de script

        if dolidb:
            dolidb.close()

        self.logger.info("THE (happy) END!\n")


#*******************************************************
# Launch main function
if __name__ == "__main__":
    script = dolibarr2Odoo()
    script.logger_ch.setLevel(logging.DEBUG)
    script.runInOdooContext()
