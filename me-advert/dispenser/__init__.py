# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from commonlib import database


# create application
app = Flask('dispenser')
app.config.from_object('dispenser_flask_conf')


# init SQLAlchemy connector
sqlserver_uri = app.config['SQLALCHEMY_DATABASE_URI']
session_autocommit = app.config['SQLALCHEMY_SESSION_AUTOCOMMIT']
session_autoflush = app.config['SQLALCHEMY_SESSION_AUTOFLUSH']
engine = create_engine(sqlserver_uri)
database.session = scoped_session(sessionmaker(autocommit=session_autocommit,
                                               autoflush=session_autoflush,
                                               bind=engine))
database.Base.query = database.session.query_property()
database.init_metadata()


# See http://flask.pocoo.org/docs/patterns/sqlalchemy/
@app.teardown_request
def shutdown_session(exception=None):
    database.session.remove()


# init views/routes
import view
