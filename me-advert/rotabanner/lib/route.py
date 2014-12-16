# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

import tornado.web

url_handlers = []


def url_route(route, name=None):
    def decorator(handler_class):
        url_handlers.append(tornado.web.url(route, handler_class, name=name))
        return handler_class
    return decorator