# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

DEBUG = True

# Period, during which we calculate sum of impressions (starts at now)
CUTOFF_CALCULATION_PERIOD = '45m'
CUTOFF_THRESHOLD_MULTIPLIER = 4

# Base URL for ad server links
ROTABANNER_URL_BASE = 'http://127.0.0.1:8080/'

# Contractor's name
CLICKER_CONTRACTOR_NAME = 'Clicker'
SB_CONTRACTOR_NAME = 'SurfingBird'

#SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:1qazxsw2@int.ovg.me:5432/advert-test?sslmode=prefer'
#SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:1qazxsw2@do-vpn.ovg.me:5432/advert-test?sslmode=prefer'
SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:eZdVgekAH_5r@37.200.69.174:5432/advert-database?sslmode=prefer'
SQLALCHEMY_SESSION_AUTOCOMMIT = False
SQLALCHEMY_SESSION_AUTOFLUSH = False