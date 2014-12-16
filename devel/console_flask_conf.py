# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

DEBUG = True

# Timezone definition
LOCAL_TZ = 'Europe/Moscow'

# Base URL for ad server links
ROTABANNER_URL_BASE = 'http://127.0.0.1:8080/'

# Rotabanner's Redis config
REDIS_HOST = 'int.ovg.me'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWD = None

SECRET_KEY = 'BswrAEWplJEmExmaYkV9dJkwZXhcesdex5ALHZfEAOcLz8SoEEMVFfIlD+CyTgTeM1VgFHF44g24E2jFwSNQd6sINvCCCBOwjG3jFWKaO'
CSRF_ENABLED = True
REMEMBER_COOKIE_NAME = "MediaEnergyDevel"
SESSION_PROTECTION = "basic"

#SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:1qazxsw2@int.ovg.me:5432/advert-test?sslmode=prefer'
SQLALCHEMY_DATABASE_URI = 'postgresql://me_advert:eZdVgekAH_5r@10.49.7.2:5432/advert-database?sslmode=prefer'
SQLALCHEMY_SESSION_AUTOCOMMIT = False
SQLALCHEMY_SESSION_AUTOFLUSH = False