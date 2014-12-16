# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

# Timezone definition
LOCAL_TZ = 'Europe/Moscow'

# Base URL for ad server links
ROTABANNER_URL_BASE = 'http://ads.edvent.ru/'

# Rotabanner's Redis config
REDIS_HOST = '10.49.7.4'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWD = None

SECRET_KEY = '5FcoGoFsj00DFAFQzqCmOkPaVzD1rkNODZnqjkHKscVivV/6XXAsYDvNDkrVykOCApNNrV7+mkUD9kHR4k0pQ+QMoZIEoo0eN4FvEaOO3'
CSRF_ENABLED = True
REMEMBER_COOKIE_NAME = "MediaEnergyProd"
SESSION_PROTECTION = "basic"

#####SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:1qazxsw2@ovg.me:5432/advert-test?sslmode=prefer'
# SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:eZdVgekAH_5r@10.49.7.2:5432/advert-database?sslmode=disable'

#### Fake database in production!!! ###
SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:eZdVgekAH_5r@10.49.7.2:5432/advert-database-mock?sslmode=prefer'

SQLALCHEMY_SESSION_AUTOCOMMIT = False
SQLALCHEMY_SESSION_AUTOFLUSH = False