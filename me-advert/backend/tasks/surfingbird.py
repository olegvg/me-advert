# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'ogaidukov'

import re
import random
import urllib
import urllib2
from bs4 import BeautifulSoup
import backend
from backend import celery
from backend.utils import SqlAlchemyTask
from commonlib import configparser
from commonlib.model import AdLog, Counter, Creative, Campaign, Contractor, CPC
from commonlib import database as db
from commonlib.database import in_time
from sqlalchemy import func
from sqlalchemy.exc import ResourceClosedError


CURRENT_STATE_FORMAT = 'https://revolver.surfingbird.ru/campaign/{}/urls'
ALTER_STATE_FORMAT = 'https://revolver.surfingbird.ru/campaign/{}/edit'
START_CAMPAIGN_FORMAT = 'https://revolver.surfingbird.ru/campaign/{}/start'
STOP_CAMPAIGN_FORMAT = 'https://revolver.surfingbird.ru/campaign/{}/stop'


def grab_url_to_bs(url, cookie):
    opener = urllib2.build_opener()
    opener.addheaders.append(('Cookie', cookie))
    html = opener.open(url).read()
    return BeautifulSoup(html, 'lxml')


def get_campaign_current_state(sb_campaign_id, cookie):
    bs = grab_url_to_bs(CURRENT_STATE_FORMAT.format(sb_campaign_id), cookie)

    day_limit_node = bs.find('span', 'b_revolver__option', text=u'Дневной лимит:')
    day_limit = day_limit_node.find_next_sibling('span', 'b_revolver__option-val').string

    impressions_today_raw = bs.find('span', 'b_revolver__option', text=u'Показов сегодня:') \
        .find_next('span', 'b_revolver__option-val').strings
    impressions_today = re.match('^([0-9]+?)\s+?', impressions_today_raw.next()).group(0)
    print day_limit, impressions_today
    return int(day_limit), int(impressions_today)


def alter_campaign_current_state(sb_campaign_id, cookie, target_clicks):
    url = ALTER_STATE_FORMAT.format(sb_campaign_id)
    bs = grab_url_to_bs(url, cookie)
    try:
        csrf_value = bs.find('input', attrs={'name': 'Magica'})['value']
    except TypeError:
        backend.logger.critical(u"SurfingBird's auth cookie has been expired or interface/auth approach changed!")
        return
    age_targeting_1 = bs.find('input', attrs={'name': 'age_targeting_1'})['value']
    age_targeting_2 = bs.find('input', attrs={'name': 'age_targeting_2'})['value']

    categories = bs.find('input', attrs={'name': 'categories'})['value']
    visit_price = bs.find('input', attrs={'name': 'visit_price'})['value']
    frequency = bs.find('select', attrs={'name': 'frequency'}) \
        .find_next('option', attrs={'selected': 'selected'})['value']
    gender_targeting = bs.find('input', attrs={'name': 'gender_targeting'})['value']
    geo_targets = bs.find('input', attrs={'name': 'geo-targets'})['value']

    form_data = {'Magica': csrf_value,
                 'daily_visit_limit': target_clicks,
                 'url': sb_campaign_id,
                 'age_targeting_1': age_targeting_1,
                 'age_targeting_2': age_targeting_2,
                 'categories': categories,
                 'daily_cost_limit': float(visit_price) * target_clicks,
                 'frequency': frequency,
                 'gender_targeting': gender_targeting,
                 'geo-targets': geo_targets,
                 'visit_price': visit_price}

    encoded_data = urllib.urlencode(form_data)
    post_opener = urllib2.build_opener()
    post_opener.addheaders.append(('Cookie', cookie))
    result = post_opener.open(url, encoded_data)
    return result.getcode()


def start_campaign(sb_campaign_id, cookie):
    opener = urllib2.build_opener()
    opener.addheaders.append(('Cookie', cookie))
    return opener.open(START_CAMPAIGN_FORMAT.format(sb_campaign_id)).getcode()


def stop_campaign(sb_campaign_id, cookie):
    opener = urllib2.build_opener()
    opener.addheaders.append(('Cookie', cookie))
    return opener.open(STOP_CAMPAIGN_FORMAT.format(sb_campaign_id)).getcode()


@celery.task
def buy_surfingbird_clicks():
    buy_surfingbird_clicks_async.delay()


@celery.task(base=SqlAlchemyTask)
def buy_surfingbird_clicks_async():
    surfingbird_cfg = configparser.config_section_obj(backend.config, 'surfingbird')
    cookie = surfingbird_cfg.cookie
    contractor_name = unicode(surfingbird_cfg.contractor_name)
    cutoff_calculation_period = surfingbird_cfg.cutoff_calculation_period

    imprs_query = Creative.query \
        .with_entities(Creative.id, func.sum(AdLog.value).label('total_imprs')) \
        .join(Creative.counters) \
        .join(Creative.cpc) \
        .join(Creative.campaign) \
        .join(Counter.logs) \
        .join(CPC.contractor) \
        .filter(AdLog.record_type == 'impr',
                Campaign.state != 'archived',
                Contractor.name == contractor_name) \
        .group_by(Creative.id) \
        .subquery('imprs_query')

    clcks_query = Creative.query \
        .with_entities(Creative.id, func.sum(AdLog.value).label('total_clcks')) \
        .join(Creative.counters) \
        .join(Creative.cpc) \
        .join(Creative.campaign) \
        .join(Counter.logs) \
        .join(CPC.contractor) \
        .filter(AdLog.record_type == 'clck',
                Campaign.state != 'archived',
                Contractor.name == contractor_name) \
        .group_by(Creative.id) \
        .subquery('clcks_query')

    try:
        dispensers = db.session.query(Creative, 'total_imprs', 'total_clcks') \
            .join(imprs_query, imprs_query.c.id == Creative.id) \
            .join(clcks_query, clcks_query.c.id == Creative.id) \
            .all()
    except ResourceClosedError:
        return

    for creative, total_imprs, total_clcks in dispensers:
        try:
            ectr = 100.0 * total_clcks / total_imprs
        except ZeroDivisionError:
            continue
        curr_cpc_provider = creative.cpc[0]

        curr_imprs_sum_res = db.session.query(Creative, func.sum(AdLog.value)) \
            .join(Creative.counters) \
            .join(Counter.logs) \
            .filter(AdLog.record_type == 'impr',
                    in_time(AdLog.time_stamp, cutoff_calculation_period),
                    Creative.id == creative.id) \
            .group_by(Creative) \
            .first()
        if curr_imprs_sum_res is None:
            continue
        curr_imprs_sum = curr_imprs_sum_res[1]

        ctr_delta = curr_cpc_provider.ctr_mean - ectr + random.gauss(0, curr_cpc_provider.ctr_deviation)
        if ctr_delta <= 0:
            stop_campaign(curr_cpc_provider.external_campaign_id, cookie)
            continue
        else:
            start_campaign(curr_cpc_provider.external_campaign_id, cookie)
        target_clicks = int(ctr_delta * curr_imprs_sum / 100.0)
        day_limit, impressions_today = get_campaign_current_state(curr_cpc_provider.external_campaign_id, cookie)
        clicks_needed_cumulative = target_clicks + impressions_today
        backend.logger.warning("Surfingbird:: campaign: {}, clicks: {}".format(curr_cpc_provider.external_campaign_id,
                                                                       clicks_needed_cumulative))
        alter_campaign_current_state(curr_cpc_provider.external_campaign_id, cookie, clicks_needed_cumulative)


@celery.task
def clear_surfingbird_campaigns():
    clear_surfingbird_campaigns_async.delay()


@celery.task(base=SqlAlchemyTask)
def clear_surfingbird_campaigns_async():
    surfingbird_cfg = configparser.config_section_obj(backend.config, 'surfingbird')
    cookie = surfingbird_cfg.cookie
    cpcs = CPC.query.all()
    for cpc in cpcs:
        stop_campaign(cpc.external_campaign_id, cookie)
        alter_campaign_current_state(cpc.external_campaign_id, cookie, 1)
