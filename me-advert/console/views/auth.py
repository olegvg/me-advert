# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from flask import request, Blueprint, render_template, redirect, url_for
from flask.ext.login import login_user, logout_user, login_required, current_user
from console.views.forms import LoginForm
from console import app, login_manager, redirectors
from console.lib.identity import Identity

auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(email):
    return Identity.get_user(email)


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("auth.login"))


@app.context_processor
def inject_current_user():
    """
        This context processor handler inserts variables 'fullname', 'role' and 'email'
        of logged in user into Jinja2 global context.
    """
    if type(current_user._get_current_object()) is Identity and current_user.is_authenticated():
        fullname = u"{} {}".format(current_user.person.first_name, current_user.person.surname)
        role = current_user.person.role
        email = current_user.person.email
        return dict(fullname=fullname, email=email, role=role)
    else:
        return {}


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # TODO add incorrect login notification here and to auth.html
    form = LoginForm()
    if form.validate_on_submit():
        identity = Identity(form.email.data, form.plain_password.data)
        if login_user(identity, remember=form.remember_me.data):
            if identity.person:
                return redirect(url_for(redirectors[identity.person.role]))
    elif isinstance(current_user._get_current_object(), Identity):
        return redirect(url_for(redirectors[current_user.person.role]))
    return render_template("auth.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index.entry"))


@auth_bp.route("/forget")
@login_required
def forget():
    # TODO do it!
    return redirect(url_for("index.entry"))


