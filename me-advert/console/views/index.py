# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from flask import Blueprint, redirect, url_for
from flask.ext.login import login_required, current_user
from console import redirectors

index_bp = Blueprint('index', __name__)


@index_bp.route("/")
@login_required
def entry():
    return redirect(url_for(redirectors[current_user.person.role]))
