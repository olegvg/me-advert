# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'ogaidukov'

import random
from flask import redirect
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from dispenser import app
from commonlib.model import AdLog, Counter, Creative, Campaign, Contractor, CPC
from commonlib.database import session, in_time


#@app.route('/dispenser', methods=['GET'])
def dispenser():
    imprs_query = Creative.query \
        .with_entities(Creative.id, func.sum(AdLog.value).label('total_imprs')) \
        .join(Creative.counters) \
        .join(Creative.cpc) \
        .join(Creative.campaign) \
        .join(Counter.logs) \
        .join(Counter.contractor) \
        .filter(AdLog.record_type == 'impr',
                Campaign.state != 'archived',
                Contractor.name == app.config['CLICKER_CONTRACTOR_NAME']) \
        .group_by(Creative.id) \
        .subquery('imprs_query')

    clcks_query = Creative.query \
        .with_entities(Creative.id, func.sum(AdLog.value).label('total_clcks')) \
        .join(Creative.counters) \
        .join(Creative.cpc) \
        .join(Creative.campaign) \
        .join(Counter.logs) \
        .join(Counter.contractor) \
        .filter(AdLog.record_type == 'clck',
                Campaign.state != 'archived',
                Contractor.name == app.config['CLICKER_CONTRACTOR_NAME']) \
        .group_by(Creative.id) \
        .subquery('clcks_query')

    dispensers = session.query(Creative, 'total_imprs', 'total_clcks') \
        .join(imprs_query, imprs_query.c.id == Creative.id) \
        .join(clcks_query, clcks_query.c.id == Creative.id) \
        .all()

    competitors = []
    for creative, total_imprs, total_clcks in dispensers:
        try:
            ectr = 100 * total_clcks / total_imprs
        except ZeroDivisionError:
            continue
        curr_dispenser = creative.cpc[0]

        imprs_sum_res = session.query(Creative, func.sum(AdLog.value)) \
            .join(Creative.counters) \
            .join(Counter.logs) \
            .filter(AdLog.record_type == 'impr',
                    in_time(AdLog.time_stamp, app.config['CUTOFF_CALCULATION_PERIOD']),
                    Creative.id == creative.id) \
            .group_by(Creative) \
            .first()
        if imprs_sum_res is None:
            continue
        imprs_sum = imprs_sum_res[1]

        # Cut-off unnecessary clicks
        cut_off_ctr = 100 / imprs_sum
        if app.config['CUTOFF_THRESHOLD_MULTIPLIER'] * cut_off_ctr > curr_dispenser.ctr_mean:
            continue

        gauss_prob = random.gauss(ectr, curr_dispenser.ctr_deviation)
        if curr_dispenser.ctr_mean > gauss_prob:
            competitors.append(curr_dispenser)

    if len(competitors) > 0:
        winner = random.choice(competitors)

        url_base = app.config['ROTABANNER_URL_BASE'].rstrip('/')
        url = '{}/clck/{}'.format(url_base, winner.target_counter.uniq_id)
        return redirect(url)
    else:
        return "We've missed!"


@app.route('/cutter/<counter_uniq_id>', methods=['GET'])
def cutter(counter_uniq_id):
    try:
        creative = Creative.query \
            .join(Creative.counters) \
            .filter(Counter.uniq_id == counter_uniq_id) \
            .one()
    except NoResultFound:
        return 'Counter is absent.'

    imprs_query = Creative.query \
        .with_entities(Creative.id, func.sum(AdLog.value).label('total_imprs')) \
        .join(Creative.counters) \
        .join(Creative.cpc) \
        .join(Creative.campaign) \
        .join(Counter.logs) \
        .join(CPC.contractor) \
        .filter(AdLog.record_type == 'impr',
                Campaign.state != 'archived',
                Contractor.name == app.config['SB_CONTRACTOR_NAME'],
                Creative.id == creative.id) \
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
                Contractor.name == app.config['SB_CONTRACTOR_NAME'],
                Creative.id == creative.id) \
        .group_by(Creative.id) \
        .subquery('clcks_query')

    try:
        dispenser = session.query(Creative, 'total_imprs', 'total_clcks') \
            .options(joinedload(Creative.cpc)) \
            .join(imprs_query, imprs_query.c.id == Creative.id) \
            .join(clcks_query, clcks_query.c.id == Creative.id) \
            .one()
    except NoResultFound:
        return 'Counter is absent!'

    (creative, total_imprs, total_clcks) = dispenser
    curr_dispenser = creative.cpc[0]

    url_base = app.config['ROTABANNER_URL_BASE'].rstrip('/')
    url = '{}/clck/{}'.format(url_base, curr_dispenser.target_counter.uniq_id)

    if curr_dispenser.is_passthru:
        return redirect(url)

    try:
        ectr = 100 * total_clcks / total_imprs
    except ZeroDivisionError:
        return "It's not started yet!"

    imprs_sum_res = session.query(Creative, func.sum(AdLog.value)) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'impr',
                in_time(AdLog.time_stamp, app.config['CUTOFF_CALCULATION_PERIOD']),
                Creative.id == creative.id) \
        .group_by(Creative) \
        .first()
    if imprs_sum_res is None:
        curr_dispenser.clicks_overloaded += 1
        session.commit()
        return "No suitable imprs!"
    imprs_sum = imprs_sum_res[1]

    # Cut-off unnecessary clicks
    cut_off_ctr = 100 / imprs_sum
    if app.config['CUTOFF_THRESHOLD_MULTIPLIER'] * cut_off_ctr > curr_dispenser.ctr_mean:
        curr_dispenser.clicks_overloaded += 1
        session.commit()
        return "Cut off!"

    gauss_prob = random.gauss(ectr, curr_dispenser.ctr_deviation)
    if curr_dispenser.ctr_mean > gauss_prob:
        return redirect(url)
    else:
        curr_dispenser.clicks_overloaded += 1
        session.commit()
        return "We've missed!"
