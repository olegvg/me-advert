# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

import os.path
import argparse
import tornado.ioloop
import tornado.httpserver
import tornado.web
from commonlib import configparser, logmaker
from rotabanner.lib import route
import redis
import pygeoip

config = None
logger = None
args = None
redisdb = None
geoip = None


def init_application():
    # TODO refactor these global variables
    global config, logger, args, redisdb, geoip
    arg_parser = argparse.ArgumentParser(description="Ad Serving daemon which built on top of Tornado")
    arg_parser.add_argument('config', help="Daemon's config file")
    arg_parser.add_argument('-D', '--debug', help="Debug mode", action='store_true')
    arg_parser.add_argument('-A', '--listen_addr', help="Listen address or '0.0.0.0'")
    arg_parser.add_argument('-L', '--listen_port', help="Listen TCP port")
    args = arg_parser.parse_args()

    config = configparser.parse_config(args.config)

    # TODO make use of standard Tornado logging streams 'tornado.access', 'tornado.application' and 'tornado.general'
    logger = logmaker.logger_from_config(config)

    redis_config = configparser.config_section_obj(config, 'redis')
    redisdb = redis.StrictRedis(host=redis_config.host, port=int(redis_config.port),
                                db=redis_config.db, password=redis_config.password)

    geoip = pygeoip.GeoIP('../me-advert/rotabanner/data/GeoIPCity.dat', pygeoip.MEMORY_CACHE)

    import handlers     # Important! Initialize url handler classes by importing


def run_application():
    init_application()
    listen_port = int(args.listen_port)
    listen_addr = args.listen_addr
    template_path=os.path.join(os.path.dirname(__file__), "templates")
    application = TornadoApp(debug=args.debug, template_path=template_path)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(listen_port, address=listen_addr)
    tornado.ioloop.IOLoop.instance().start()


class TornadoApp(tornado.web.Application):
    def __init__(self, **settings):
        logger.info("Starting Tornado application instance")
        tornado.web.Application.__init__(self, route.url_handlers, **settings)