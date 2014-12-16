# -*- coding: utf-8 -*-

from __future__ import with_statement

__author__ = 'ogaidukov'

from abc import ABCMeta, abstractmethod
from functools import partial
import datetime
import tornado.web
import tornado.gen
from redis.exceptions import ConnectionError
from rotabanner.lib.exceptions import CeleryTimeoutException
from rotabanner import application as app
from commonlib import configparser
from backend.tasks import servant


application_config = configparser.config_section_obj(app.config, 'application')
log_time_interval = int(application_config.log_time_interval)
celery_soft_timeout = int(application_config.celery_soft_timeout)
celery_hard_timeout = int(application_config.celery_hard_timeout)


class UtilsMixin(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self):
        pass

    @tornado.gen.coroutine
    def increment_counter(self, evt_type, counter_id):
        curr_epoch_time = int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds())
        time_interval = curr_epoch_time - curr_epoch_time % log_time_interval
        log_record_key = "{}-{}-{}".format(evt_type, counter_id, time_interval)
        changed_set_key = "counter-{}-changed-set".format(counter_id)
        total_events_key = "total-{}-{}".format(evt_type, counter_id)
        with app.redisdb.pipeline() as pipe:
            pipe.incr(log_record_key)
            pipe.incr(total_events_key)
            pipe.sadd(changed_set_key, log_record_key)
            pipe.execute()

    @tornado.gen.coroutine
    def validate_event(self, evt_type, uniq_id):
        with app.redisdb.pipeline() as pipe:
            pipe.get('creative-geo-cities-{}'.format(uniq_id))
            pipe.get('creative-geo-countries-{}'.format(uniq_id))
            (cities_string, countries_string) = pipe.execute()

        # neither set of cities nor set of countries is selected so bypass geo check
        try:
            if len(cities_string + countries_string) == 0:
                raise tornado.gen.Return(evt_type)
        except TypeError:
            raise tornado.gen.Return(evt_type)
        cities = cities_string.split(u'|')
        countries = countries_string.split(u'|')
        remote_ip = self.request.headers.get('X-Real-IP', self.request.remote_ip)
        geodata = app.geoip.record_by_addr(remote_ip)
        if geodata is not None and (geodata['city'] in cities or geodata['country_code'] in countries):
            return evt_type
        else:
            app.logger.error('Reject by geo. Address:{}, ad tag: {}'.format(remote_ip, uniq_id))
            return evt_type + '_rej_geo'

    @tornado.gen.coroutine
    def init_counter_async(self, uniq_id):
        try:
            state = app.redisdb.get('counter-{}'.format(uniq_id))
            # counter in Redis haven't initialised yet. Initialise counter via Celery.
            if not state:
                init_task = servant.init_redis_with_counter.delay(uniq_id)
                counter_key = yield tornado.gen.Task(self.celery_get_result_async, init_task)
                # return error (False) and go on because it's already been processed by backend
                if not counter_key:
                    raise tornado.gen.Return(False)
            # counter has been initialised so everything is okay
            raise tornado.gen.Return(True)
        except ConnectionError:
            app.logger.critical(u"Connection to redis server failed")
        except CeleryTimeoutException:
            app.logger.critical(u"Celery task 'init_redis_with_counter' haven't run in the time")
        # return error (False) because one of exceprions has been fired
        raise tornado.gen.Return(False)

    def celery_get_result_async(self, task, callback):
        def check_for_result(task, callback):
            if task.ready():
                callback(task.result)
            else:
                tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(
                    milliseconds=celery_soft_timeout),
                    partial(check_for_result, task, callback))

        def process_hard_timeout():
            if not task.ready():
                raise CeleryTimeoutException

        check_for_result(task, callback)
        tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(
            milliseconds=celery_hard_timeout), process_hard_timeout)