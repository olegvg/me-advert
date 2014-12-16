# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from flask import Flask, render_template, request
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import redis
from commonlib import database
from flask.ext.login import LoginManager
from flask_wtf.csrf import CsrfProtect
import pytz


# create application
app = Flask('console')
app.config.from_object('console_flask_conf')

# init Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
redirectors = {
    'manager': "manager.organizations",
    'customer': "client.overview",
    'contractor': "contractor.summary"
}

# init jinja2 extensions
app.jinja_options['extensions'].append('jinja2.ext.loopcontrols')

# init time zone info
local_tz = pytz.timezone(app.config['LOCAL_TZ'])
utc_tz = pytz.timezone('UTC')

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

# init Redis
redis_host = app.config['REDIS_HOST']
redis_port = app.config['REDIS_PORT']
redis_db = app.config['REDIS_DB']
redis_password = app.config['REDIS_PASSWD']
database.redisdb = redis.StrictRedis(host=redis_host, port=redis_port,
                                     db=redis_db, password=redis_password)


# See http://flask.pocoo.org/docs/patterns/sqlalchemy/
@app.teardown_request
def shutdown_session(exception=None):
    database.session.remove()


# Setup 404 error handler
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


# Setup 500 error handler
@app.errorhandler(500)
def general_error(error):
    return render_template('critical_error.html'), 404


# Setup distinguisher between Edvent and MediaEnergy. Needs for logo rendering.
@app.context_processor
def distinguisher():
    try:
        app_type = request.headers['X-App-Type']
    except KeyError:
        app_type = 'MediaEnergy'
    return {'app_type': app_type}


# init Flask-WTF's CSRF protection
# csrf = CsrfProtect()
# csrf.init_app(app)

# init modules/routes
import views

#print app.url_map