# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'ogaidukov'


from collections import defaultdict
from flask import Blueprint, render_template
from flask.ext.login import login_required, current_user
from console.lib import funcs
from console.lib.identity import contractor_required
from sqlalchemy import func
from commonlib.database import session
from commonlib.model import Campaign, Creative, \
    Counter, AdLog, Organization, Contractor

contractor_bp = Blueprint('contractor', __name__)


@contractor_bp.route("/summary", methods=["GET"])
@login_required
@contractor_required
def summary():
    contractor = current_user.person.contractor

    def query_template(query_obj):
        return query_obj \
            .join(Organization.campaigns) \
            .join(Campaign.creatives) \
            .join(Creative.counters) \
            .join(Counter.logs) \
            .join(Counter.contractor) \
            .filter(Contractor.id == contractor.id)

    counter_impressions = query_template(session.query(Counter, func.sum(AdLog.value))) \
        .filter(AdLog.record_type == 'impr') \
        .group_by(Counter)\
        .all()
    counter_impressions_rej_geo = query_template(session.query(Counter, func.sum(AdLog.value))) \
        .filter(AdLog.record_type == 'impr_rej_geo') \
        .group_by(Counter)\
        .all()
    counter_impressions_rej_browser = query_template(session.query(Counter, func.sum(AdLog.value))) \
        .filter(AdLog.record_type == 'impr_rej_browser') \
        .group_by(Counter)\
        .all()
    counter_clicks = query_template(session.query(Counter, func.sum(AdLog.value))) \
        .filter(AdLog.record_type == 'clck') \
        .group_by(Counter, Contractor.name)\
        .all()
    counter_clicks_rej_geo = query_template(session.query(Counter, func.sum(AdLog.value))) \
        .filter(AdLog.record_type == 'clck_rej_geo') \
        .group_by(Counter)\
        .all()
    counter_clicks_rej_browser = query_template(session.query(Counter, func.sum(AdLog.value))) \
        .filter(AdLog.record_type == 'clck_rej_browser') \
        .group_by(Counter)\
        .all()

    counter_mix = defaultdict(dict)
    for impr in counter_impressions:
        counter = impr[0]
        val = impr[1]
        if val == 0:
            continue
        geo_countries = counter.creative.geo_countries
        geo_cities = counter.creative.geo_cities
        counter_mix[counter.id].update({'counter_id': counter.id,
                                        'campaign_name': counter.creative.campaign.name,
                                        'creative_name': counter.creative.name,
                                        'creative_format_name': counter.creative.creative_format.get_full_name(),
                                        'counter_description': counter.description,
                                        'realstart_date': counter.realstart_date,
                                        'due_date': counter.creative.campaign.due_date,
                                        'geo_cities': geo_cities if geo_cities else [],
                                        'geo_countries': geo_countries if geo_countries else [],
                                        'mu_ctr': counter.mu_ctr,
                                        'sigma_ctr': counter.sigma_ctr,
                                        'impr': val})
    for summary in counter_impressions_rej_geo:
        counter = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        counter_mix[counter.id].update({'impr_rej_geo': val})
    for summary in counter_impressions_rej_browser:
        counter = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        counter_mix[counter.id].update({'impr_rej_browser': val})

    for clck in counter_clicks:
        counter = clck[0]
        val = clck[1]
        counter_mix[counter.id].update({'counter_id': counter.id,
                                        'clck': val})
    for summary in counter_clicks_rej_geo:
        counter = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        counter_mix[counter.id].update({'clck_rej_geo': val})
    for summary in counter_clicks_rej_browser:
        counter = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        counter_mix[counter.id].update({'clck_rej_browser': val})
    counters = counter_mix.values()
    for d in counters:
        try:
            d['ctr'] = '{0:0.02f}'.format(d['clck'] / d['impr'] * 100.0)
        except (TypeError, KeyError):
            d['ctr'] = '{0:0.02f}'.format(0.0)
        except ZeroDivisionError:
            d['ctr'] = '&infin;'
        try:
            d['impr'] = funcs.format_decimal(d['impr'])
        except KeyError:
            pass
        try:
            d['clck'] = funcs.format_decimal(d['clck'])
        except KeyError:
            pass

    return render_template('contractor/summary.html',
                           counters=counters,
                           contractor=contractor)
