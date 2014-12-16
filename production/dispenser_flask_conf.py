# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

# Period, during which we calculate sum of impressions (starts at now)
CUTOFF_CALCULATION_PERIOD = '45 minutes'
CUTOFF_THRESHOLD_MULTIPLIER = 4

# Base URL for ad server links
ROTABANNER_URL_BASE = 'http://ads.edvent.ru/'

# Rotabanner's Redis config
REDIS_HOST = '10.49.7.4'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWD = None

# Contractor's name
CLICKER_CONTRACTOR_NAME = 'Clicker'
SB_CONTRACTOR_NAME = 'SurfingBird'

#####SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:1qazxsw2@ovg.me:5432/advert-test?sslmode=prefer'
SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:eZdVgekAH_5r@10.49.7.2:5432/advert-database?sslmode=disable'
SQLALCHEMY_SESSION_AUTOCOMMIT = False
SQLALCHEMY_SESSION_AUTOFLUSH = False