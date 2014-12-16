# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'ogaidukov'

from datetime import datetime, timedelta
from collections import defaultdict
from itertools import tee, izip
from flask import Blueprint
from flask import request, render_template, redirect, jsonify, url_for
from flask.ext.login import login_required, current_user
from console import utc_tz, local_tz
from console.lib.identity import manager_required
from console import redirectors
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from commonlib.database import session
from commonlib.model import Campaign, Creative, Counter, AdLog


stats_bp = Blueprint('stats', __name__)


@stats_bp.route("/stats_by_campaign/<int:campaign_id>")
@login_required
@manager_required
def stats_by_campaign(campaign_id):
    try:
        campaign = session.query(Campaign) \
            .options(joinedload(Campaign.organization)) \
            .filter(Campaign.id == campaign_id,
                    Campaign.state != 'archived')\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    return render_template('stats/stats_by_campaign.html',
                           campaign=campaign)


@stats_bp.route("/stats_by_creative/<int:creative_id>")
@login_required
@manager_required
def stats_by_creative(creative_id):
    try:
        creative = session.query(Creative) \
            .options(joinedload(Creative.campaign,
                                Campaign.organization)) \
            .join(Campaign.creatives) \
            .filter(Creative.id == creative_id,
                    Campaign.state != 'archived')\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    return render_template('stats/stats_by_creative.html',
                           creative=creative)


@stats_bp.route("/stats_by_counter/<int:counter_id>")
@login_required
@manager_required
def stats_by_counter(counter_id):
    try:
        counter = session.query(Counter) \
            .options(joinedload(Counter.creative,
                                Creative.campaign,
                                Campaign.organization),
                     joinedload(Counter.contractor)) \
            .join(Campaign.creatives) \
            .join(Creative.counters) \
            .filter(Counter.id == counter_id,
                    Campaign.state != 'archived')\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    return render_template('stats/stats_by_counter.html',
                           counter=counter)


@stats_bp.route("/stats_by_campaign_ajax/<int:campaign_id>", methods=["GET"])
@login_required
@manager_required
def stats_by_campaign_ajax(campaign_id):
    query_template = session.query(Campaign) \
        .filter(Campaign.id == campaign_id)
    return prepare_stats(query_template)


@stats_bp.route("/stats_by_creative_ajax/<int:creative_id>", methods=["GET"])
@login_required
@manager_required
def stats_by_creative_ajax(creative_id):
    query_template = session.query(Creative) \
        .filter(Creative.id == creative_id)
    return prepare_stats(query_template)


@stats_bp.route("/stats_by_counter_ajax/<int:counter_id>", methods=["GET"])
@login_required
@manager_required
def stats_by_counter_ajax(counter_id):
    query_template = session.query(Counter) \
        .filter(Counter.id == counter_id)
    return prepare_stats(query_template)


def prepare_stats(query_template):
    start_datetime = request.args.get('start_datetime', '01.01.1970 00:00')
    end_datetime = request.args.get('end_datetime', '01.01.2970 00:00')
    try:
        start_datetime = datetime.strptime(start_datetime, '%d.%m.%Y %H:%M')
        end_datetime = datetime.strptime(end_datetime, '%d.%m.%Y %H:%M')
    except ValueError:
        return jsonify()

    scale = request.args.get('scale', 'day')
    if scale == 'hour':
        sqla_timedate_field = AdLog.date_to_hour_stamp
        datetime_interval = timedelta(hours=1)
    elif scale == 'day':
        sqla_timedate_field = AdLog.date_stamp
        datetime_interval = timedelta(days=1)
    else:
        return jsonify()

    query_template = query_template \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.state != 'archived',
                sqla_timedate_field.between(start_datetime, end_datetime))

    summary = defaultdict(dict)

    imprs_data = query_template \
        .with_entities(sqla_timedate_field, func.sum(AdLog.value)) \
        .filter(AdLog.record_type == 'impr') \
        .group_by(sqla_timedate_field) \
        .all()
    for k, v in imprs_data:
        if k:
            summary[k]['imprs'] = v

    clcks_data = query_template \
        .with_entities(sqla_timedate_field, func.sum(AdLog.value)) \
        .filter(AdLog.record_type == 'clck') \
        .group_by(sqla_timedate_field) \
        .all()
    for k, v in clcks_data:
        if k:
            summary[k]['clcks'] = v

    for k in summary.itervalues():
        try:
            k['ctr'] = '{0:0.02f}'.format(k['clcks'] / k['imprs'] * 100.0)
        except (TypeError, KeyError):
            k['ctr'] = '{0:0.02f}'.format(0.0)
        except ZeroDivisionError:
            k['ctr'] = '&infin;'

    s = sorted(summary.iterkeys())
    f, s = tee(s)
    next(s, None)
    for least, most in izip(f, s):
        current = least + datetime_interval
        while current != most:
            summary[current] = {'imprs': 0, 'clcks': 0, 'ctr': '{0:0.02f}'.format(0.0)}
            current += datetime_interval

    result = []
    for k, v in summary.iteritems():
        result.append([
            utc_tz.localize(k).astimezone(local_tz).strftime('%d.%m.%Y %H:%M') if isinstance(k, datetime)
            else k.strftime('%d.%m.%Y'),
            v.get('imprs', 0),
            v.get('clcks', 0),
#            format_decimal(v.get('imprs', 0)),
#            format_decimal(v.get('clcks', 0)),
            v['ctr']
        ])
    return jsonify({'aaData': result})
