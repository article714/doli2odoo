#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
'''

import importlib
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

        list_processors = self.getConfigValue("processors").split(',')
        for p in list_processors:
            self.logger.info("Will process " + str(p))
            try:
                mod = mod = importlib.import_module(str(p))
                if mod != None:
                    try:
                        mod.process(self.logger, self.env, self.cr, dolidb)
                    except:
                        self.logger.exception("Not able to process " + str(p))
            except:
                self.logger.exception("Not able to import " + str(p))
                continue

        if dolidb:
            dolidb.close()

        self.logger.info("THE (happy) END!\n")


#*******************************************************
# Launch main function
if __name__ == "__main__":
    script = dolibarr2Odoo()
    script.logger_ch.setLevel(logging.DEBUG)
    script.runInOdooContext()
