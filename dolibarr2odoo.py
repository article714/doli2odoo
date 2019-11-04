#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on march 2018

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
"""

import importlib

import mysql.connector
from odootools import OdooScript


# *************************************
# Mail Class
class dolibarr2Odoo(OdooScript.Script):

    # *************************************************************
    # overriden constructor

    def __init__(self):
        """
        constructor
        """
        OdooScript.Script.__init__(self)

        self.processor = None
        self.processed = []
        self.dolidb = None

    def run_processor(self, module_name):
        """
        Run a processor function, running dependencies before when needed
        """
        try:
            mod = importlib.import_module("dataprocessors.%s" % str(module_name))
            if mod is not None:
                dependencies = getattr(mod, "depends", False)
                if dependencies:
                    for dep in dependencies:
                        self.run_processor(dep)
                try:
                    if mod not in self.processed:
                        mod.process(self.logger, self.env, self.cr, self.dolidb)
                        self.processed.append(mod)
                except Exception:
                    self.logger.exception("Not able to process %s", str(module_name))
            else:
                self.logger.exception("Not able to import %s", str(module_name))

        except Exception:
            self.logger.exception("Not able to import %s", str(module_name))

    # ********************************************************************************
    # main script

    def run(self):
        """
        main script
        """

        # *************************************************************
        # connect to DolibarrDb
        try:
            self.dolidb = mysql.connector.connect(
                user=self.getConfigValue("dolibarr_user"),
                password=self.getConfigValue("dolibarr_pwd"),
                host=self.getConfigValue("dolibarr_host"),
                database=self.getConfigValue("dolibarr_db"),
            )
        except mysql.connector.Error as err:
            self.logger.info(err)
            return -1

        processors = self.getConfigValue("processors")
        if processors == "*":
            mod = importlib.import_module("dataprocessors")
            list_processors = []
            for m in filter(lambda s: s[0] != "_", dir(mod)):
                list_processors.append(m)
        else:
            list_processors = [p.strip() for p in processors.split(",")]

        for p in list_processors:
            self.run_processor(p)

        if self.dolidb:
            self.dolidb.close()

        self.logger.info("THE (happy) END!\n")


# *******************************************************
# Launch main function
if __name__ == "__main__":
    script = dolibarr2Odoo()
    script.runInOdooContext()
