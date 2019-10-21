# -*- coding: utf-8 -*-

"""
Created on october 2019

Utility functions to convert data


@author: C. Guychard
@copyright: ©2018 Article714
@license: AGPL
"""

import mysql.connector

from odootools.Converters import toString

# dataprocessors we depend on

depends = ["contact", "product", "payment_term"]


def process(logger, odooenv, odoocr, dolidb):
    """
    Do the Job for supplier invoices
    """
    try:
        dolicursor = dolidb.cursor()

        dolicursor.execute(
            """ SELECT c.rowid, c.ref, c.ref_client, c.date_creation,c.date_valid, c.date_cloture,
                        s.nom, t.libelle
                               FROM llx_societe s, llx_commande c
                               LEFT OUTER JOIN llx_c_payment_term t on c.fk_cond_reglement = t.rowid
                               WHERE c.fk_soc=s.rowid;"""
        )

        dolicursor.close()
    except mysql.connector.Error as err:
        logger.error("SQL Error: " + str(err))
        return -1
