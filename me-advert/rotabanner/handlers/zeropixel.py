# -*- coding: utf-8 -*-

from __future__ import with_statement

__author__ = 'ogaidukov'

import random
import tornado.web
import tornado.gen
from redis.exceptions import ConnectionError
from rotabanner.lib import resource
from rotabanner.lib.route import url_route
from rotabanner import application as app
from rotabanner.lib.utils import UtilsMixin


class SpecRequestHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def rest_of_click(self, uniq_id):
        try:
            redirect_url = app.redisdb.get('counter-{}-clck-target-url'.format(uniq_id))
        except ConnectionError:
            app.logger.critical(u"Connection to Redis server failed")
            redirect_url = None
        # any unhandled exception must be passed out
        except Exception, e:
            import traceback
            app.logger.critical(u"Unknown exception "
                                u"in 'ClicksHandler': '{}'".format(traceback.format_exc(e)))
            redirect_url = None
        if redirect_url is not None and (redirect_url[0:7] == u'http://' or redirect_url[0:8] == u'https://'):
            self.redirect(redirect_url, permanent=False)
        # We lose this click but try to do some recovery work
        else:
            referer_url = self.request.headers.get('Referer')
            if referer_url:
                app.logger.critical(u"Redirecting back to referer url instead of landing page. "
                                    u"Counter_id is '{}'".format(uniq_id))
                self.redirect(referer_url, permanent=False)
            # We have no chance to recovery and compelled to show 'error' message instead of redirect to target url
            else:
                app.logger.critical(u"We have to show 'error' message instead of redirecting to landing page. "
                                    u"We have absolutely no chance because we know "
                                    u"neither url of landing page nor user's referer url. "
                                    u"Counter_id is '{}'".format(uniq_id))
                self.write(u'Ошибка!')
                self.finish()

    @tornado.gen.coroutine
    def rest_of_impression(self, uniq_id):
        try:
            redirect_url = app.redisdb.get('counter-{}-impr-target-url'.format(uniq_id))
        except ConnectionError:
            app.logger.critical(u"Connection to Redis server failed")
            redirect_url = None
        # any unhandled exception must be passed out
        except Exception, e:
            import traceback
            app.logger.critical(u"Unknown exception "
                                u"in 'ImpressionsHandler': '{}'".format(traceback.format_exc(e)))
            redirect_url = None

        if redirect_url is not None and (redirect_url[0:7] == 'http://' or redirect_url[0:8] == 'https://'):
            self.redirect(redirect_url, permanent=False)
        # We are at the last of chain so show the pixel
        else:
            self.set_header("Content-Type", "image/gif")
            self.write(resource.transparent_image)
            self.finish()


@url_route("/impr/(\w{64}).*")
class ImpressionsHandler(SpecRequestHandler, UtilsMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, uniq_id):
        # Initialise counter and finish HTTP response in case of any type of error
        if (yield tornado.gen.Task(self.init_counter_async, uniq_id)) is False:
            self.finish()
            return
        evt = yield self.validate_event('impr', uniq_id)
        yield self.increment_counter(evt, uniq_id)
        if evt is 'impr':
            yield self.rest_of_impression(uniq_id)
        else:
            self.set_header("Content-Type", "image/gif")
            self.write(resource.transparent_image)
            self.finish()


@url_route("/clck/(\w{64}).*")
class ClicksHandler(SpecRequestHandler, UtilsMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, uniq_id):
        # Initialise counter and finish HTTP response in case of any type of error
        if (yield tornado.gen.Task(self.init_counter_async, uniq_id)) is False:
            self.finish()
            return
        evt = yield self.validate_event('clck', uniq_id)
        yield self.increment_counter(evt, uniq_id)
        if evt is 'clck':
            yield self.rest_of_click(uniq_id)
        else:
            self.write(u'Извините, вы не входите в целевую аудиторию!')
            self.finish()


@url_route("/cpcimpr/(\w{64}).*")
class CPCImpressionsHandler(SpecRequestHandler, UtilsMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, uniq_id):
        # Initialise counter and finish HTTP response in case of any type of error
        if (yield tornado.gen.Task(self.init_counter_async, uniq_id)) is False:
            self.finish()
            return
        evt = yield self.validate_event('impr', uniq_id)
        if evt is not 'impr':
            yield self.increment_counter(evt, uniq_id)
            self.set_header("Content-Type", "image/gif")
            self.write(resource.transparent_image)
            self.finish()
            return

        ctr = app.redisdb.get("counter-gross-ctr-{}".format(uniq_id))
        try:
            ctr = float(ctr)
        except TypeError:
            with app.redisdb.pipeline() as pipe:
                pipe.get("total-impr-{}".format(uniq_id))
                pipe.get("total-clck-{}".format(uniq_id))
                (impr_count, clck_count) = pipe.execute()
            try:
                ctr = 100.0 * float(clck_count) / float(impr_count)
            except (ZeroDivisionError, TypeError):
                ctr = 100.0
        with app.redisdb.pipeline() as pipe:
            pipe.get('counter-{}-cpc-mu-ctr'.format(uniq_id))
            pipe.get('counter-{}-cpc-sigma-ctr'.format(uniq_id))
            (mu_ctr, sigma_ctr) = pipe.execute()
        try:
            mu_ctr = float(mu_ctr)
            sigma_ctr = float(sigma_ctr)
            threshold = random.gauss(mu_ctr, sigma_ctr)  # deviation of CTR
        except (TypeError, ValueError):
            threshold = 0.0
        if ctr >= threshold:
            yield self.increment_counter('impr', uniq_id)
            yield self.rest_of_impression(uniq_id)
        else:
            yield self.increment_counter('impr_rej_cpc', uniq_id)
            self.set_header("Content-Type", "image/gif")
            self.write(resource.transparent_image)
            self.finish()