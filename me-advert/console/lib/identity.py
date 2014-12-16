# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from functools import wraps
from flask import redirect, url_for
from console import login_manager
from flask.ext.login import UserMixin, current_user
from commonlib.model import Person


class Identity(UserMixin):
    def __init__(self, email, password, is_password_plain=True, person=None):
        password = unicode(password) if is_password_plain is True else password
        if is_password_plain is True:
            # It's a login time!
            self.person = person if isinstance(person, Person) \
                else Person.query.filter_by(email=email, is_blocked=False).first()
            if self.person is not None and self.person.check_password(password) is True:
                self._is_authenticated = True
            else:
                self._is_authenticated = False
        else:
            # Password has already checked when it was plain so we assume is_authenticated = True
            # Seems to be no danger in this approach. Beware!
            self.person = person if isinstance(person, Person) \
                else Person.query.filter_by(email=email, is_blocked=False).one()
            self._is_authenticated = True

    def is_authenticated(self):
        return self._is_authenticated

    def get_id(self):
        return self.person.email if self.person else None

    @classmethod
    def get_user(cls, email):
        person = Person.query.filter_by(email=email, is_blocked=False).first()
        return Identity(email, None, is_password_plain=False, person=person) if person else None


def manager_required(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        if isinstance(current_user._get_current_object(), Identity) and current_user.person.role == 'manager':
            return func(*args, **kwargs)
        else:
            return redirect(url_for(login_manager.login_view))
    return decorator


def contractor_required(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        if isinstance(current_user._get_current_object(), Identity) and current_user.person.role == 'contractor':
            return func(*args, **kwargs)
        else:
            return redirect(url_for(login_manager.login_view))
    return decorator