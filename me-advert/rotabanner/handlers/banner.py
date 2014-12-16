# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

import tornado.web
import tornado.gen
import tornado.template
from rotabanner.lib.utils import UtilsMixin
from rotabanner.lib.route import url_route
from rotabanner import application as app
from redis.exceptions import ConnectionError


@url_route("/iframe/(\w{64})\.html.*")
class BannerHandler(tornado.web.RequestHandler, UtilsMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, uniq_id):
        # Initialise counter and finish HTTP response in case of any type of error
        if (yield tornado.gen.Task(self.init_counter_async, uniq_id)) is False:
            self.finish()
            return
        try:
            with app.redisdb.pipeline() as pipe:
                pipe.get("counter-{}-banner-dimensions".format(uniq_id))
                pipe.get("counter-{}-banner-exts".format(uniq_id))
                (dimensions, exts) = pipe.execute()
        except ConnectionError:
            app.logger.critical(u"Connection to redis server failed")
            self.finish()
            return
        try:
            dim_x, dim_y = dimensions.split(u'x')
            dim_x = int(dim_x)
            dim_y = int(dim_y)
        except (ValueError, AttributeError):
            app.logger.critical(u"Can't get dimensions of banner {}".format(uniq_id))
            self.finish()
            return
        try:
            first_ext, second_ext = exts.split(u',')
        except ValueError:
            first_ext, second_ext = None, None
        self.render('banner.html', uid=uniq_id, dim_x=dim_x, dim_y=dim_y, first_ext=first_ext, second_ext=second_ext)
