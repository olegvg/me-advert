# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from console import app

from index import index_bp
from auth import auth_bp
from manager import manager_bp
from stats import stats_bp
from client import client_bp
from contractor import contractor_bp


app.register_blueprint(index_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(manager_bp, url_prefix='/manager')
app.register_blueprint(stats_bp, url_prefix='/stats')
app.register_blueprint(client_bp, url_prefix='/client')
app.register_blueprint(contractor_bp, url_prefix='/contractor')