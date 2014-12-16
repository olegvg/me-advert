# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'ogaidukov'


import datetime
import itertools
import random
import math
from commonlib import database as db
from commonlib.database import session
from commonlib.model import Campaign, Creative, Site, Counter, AdLog
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError, ResourceClosedError
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import InvalidRequestError
import backend
from backend import celery
from redis.exceptions import ConnectionError
from backend.utils import SqlAlchemyTask, iterate_redis_set


@celery.task
def store_events():
    store_events_async.delay()


@celery.task(base=SqlAlchemyTask)
def store_events_async():
    creatives = Creative.query\
        .join(Campaign.creatives)\
        .options(joinedload(Creative.counters))\
        .filter(Campaign.state != 'archived')\
        .all()
    counters = tuple(itertools.chain.from_iterable(map(lambda c: c.counters, creatives)))
    for counter in counters:
        changed_set_key = 'counter-{}-changed-set'.format(counter.uniq_id)
        for log_record_key in iterate_redis_set(changed_set_key):
            with db.redisdb.pipeline() as pipe:
                pipe.get(log_record_key)
                pipe.delete(log_record_key)
                amount = pipe.execute()[0]   # result of pipe.get()
            (event_type, id, time_stamp) = log_record_key.split('-')
            date_time = datetime.datetime.utcfromtimestamp(float(time_stamp))
            log_record = AdLog(counter, event_type, date_time, amount)
            try:
                db.session.begin()
                db.session.add(log_record)
                db.session.commit()
            except SQLAlchemyError:
                with db.redisdb.pipeline() as pipe:
                    pipe.incr(log_record_key, amount)
                    pipe.sadd(changed_set_key, log_record_key)
                    try:
                        pipe.execute()
                    except ConnectionError:
                        backend.logger.critical(u"Connection to Redis server failed while rollback transaction")
                backend.logger.error(u"Transaction error while adding "
                                     u"AdLog record for counter '{}'".format(counter.uniq_id))
                return


@celery.task
def recalculate_ctrs():
    recalculate_ctrs_async.delay()


@celery.task(base=SqlAlchemyTask)
def recalculate_ctrs_async():
    imprs_query = Counter.query \
        .with_entities(Counter.id, func.sum(AdLog.value).label('total_imprs')) \
        .join(Creative.counters) \
        .join(Creative.campaign) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'impr',
                Campaign.state != 'archived') \
        .group_by(Counter.id) \
        .subquery('imprs_query')

    clcks_query = Counter.query \
        .with_entities(Counter.id, func.sum(AdLog.value).label('total_clcks')) \
        .join(Creative.counters) \
        .join(Creative.campaign) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'clck',
                Campaign.state != 'archived') \
        .group_by(Counter.id) \
        .subquery('clcks_query')

    try:
        totals = db.session.query(Counter, 'total_imprs', 'total_clcks') \
            .join(imprs_query, imprs_query.c.id == Counter.id) \
            .join(clcks_query, clcks_query.c.id == Counter.id) \
            .all()
    except ResourceClosedError:
        print "Error: can't calculate totals"
        return

    for row in totals:
        counter = row[0]
        total_impressions = row[1] if row[1] else 0
        total_clicks = row[2] if row[2] else 0

        try:
            total_ctr = total_clicks / total_impressions * 100.0
        except (ZeroDivisionError, TypeError):
            total_ctr = 100.0

        db.redisdb.set("counter-gross-ctr-{}".format(counter.uniq_id), total_ctr)


@celery.task(base=SqlAlchemyTask)
def check_realstart_dates():
    pass


@celery.task(base=SqlAlchemyTask)
def check_campaign_period():
    # TODO Write check_campaign_period()
    pass


@celery.task(base=SqlAlchemyTask)
def update_per_campaign_sites_report():
    update_per_campaign_sites_report_async.delay()


@celery.task(base=SqlAlchemyTask)
def update_per_campaign_sites_report_async():
    campaigns_with_sites_subq = Campaign.query \
        .with_entities(Campaign.id, func.count(Site.id).label('sites_per_campaign')) \
        .join(Campaign.sites) \
        .group_by(Campaign.id) \
        .filter(Campaign.state != 'archived') \
        .subquery()

    impressions_summary = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .join(campaigns_with_sites_subq, campaigns_with_sites_subq.c.id == Campaign.id) \
        .filter(AdLog.record_type == 'impr',
                AdLog.date_stamp == datetime.date.today() - datetime.timedelta(days=1),
                campaigns_with_sites_subq.c.sites_per_campaign > 0) \
        .group_by(Campaign) \
        .all()

    impresson_threshold = 40  # Number of imprs behind which we assume there no significant impressions and will ignore
    impression_frequency = 2.4

    for impr_tuple in impressions_summary:
        campaign = impr_tuple[0]
        imprs = impr_tuple[1]

        if imprs < impresson_threshold:
            continue

        sites = campaign.sites
        sites_num = len(sites)
        sites_in_rep_num = sum(map(lambda x: 1 if x.is_hit else 0, sites))
        sites_to_rep_num = math.ceil((sites_num - sites_in_rep_num) / random.uniform(3.0, 5.0))
        sites_to_rep_num = int(min(sites_num - sites_in_rep_num, imprs / impression_frequency, sites_to_rep_num))

        sites_to_modify = filter(lambda s: not s.is_hit, sites)[:sites_to_rep_num]
        session.begin()
        for site in sites_to_modify:
            site.is_hit = True
        session.commit()
