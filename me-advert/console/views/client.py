# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'ogaidukov'

from datetime import datetime
from calendar import timegm
from collections import defaultdict
from flask import request, Blueprint, render_template, redirect, url_for, jsonify
from flask.ext.login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from console import local_tz, utc_tz, redirectors
from console.lib import funcs
from commonlib.model import Campaign, Creative, Counter, AdLog, Person, Organization, Site
from commonlib.database import session


client_bp = Blueprint('client', __name__)


@client_bp.route("/overview")
@login_required
def overview():
    org = current_user.person.organization
    if not org:
        return render_template('critical_error.html')

    active_campaigns = Campaign.query \
        .join(Organization.campaigns,
              Organization.persons) \
        .filter(Campaign.state == 'active',
                Person.id == current_user.person.id)\
        .count()
    inactive_campaigns = Campaign.query \
        .join(Organization.campaigns,
              Organization.persons) \
        .filter(Campaign.state.in_(['paused', 'completed']),
                Person.id == current_user.person.id)\
        .count()

    archived_campaigns = Campaign.query \
        .join(Organization.campaigns,
              Organization.persons) \
        .filter(Campaign.state == 'archived',
                Person.id == current_user.person.id)\
        .count()

    query_template = session.query(func.sum(AdLog.value)) \
        .join(Organization.campaigns,
              Organization.persons) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Person.id == current_user.person.id,
                Campaign.state != 'archived')

    total_impressions = query_template \
        .filter(Person.id == current_user.person.id,
                AdLog.record_type == 'impr') \
        .first()[0]

    total_clicks = query_template \
        .filter(Person.id == current_user.person.id,
                AdLog.record_type == 'clck') \
        .first()[0]

    try:
        ctr = '{0:0.02f}'.format(total_clicks / total_impressions * 100.0)
    except (ZeroDivisionError, TypeError):
        ctr = '{0:0.02f}'.format(0.0)

    staff_raw = Person.query \
        .filter(Organization.id == org.id) \
        .join(Organization.persons) \
        .order_by('surname') \
        .all()
    staff = []
    for st in staff_raw:
        staff.append(u'{} {}'.format(st.first_name, st.surname))
    return render_template('client/overview.html',
                           org=org,
                           active_campaigns=active_campaigns,
                           inactive_campaigns=inactive_campaigns,
                           archived_campaigns=archived_campaigns,
                           staff=', '.join(staff),
                           total_impressions=funcs.format_decimal(total_impressions) if total_impressions else 0,
                           total_clicks=funcs.format_decimal(total_clicks) if total_clicks else 0,
                           ctr=ctr)


@client_bp.route("/campaigns")
@login_required
def campaigns():
    mix = defaultdict(dict)

    query_template = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Organization.persons,
              Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Person.id == current_user.person.id,
                Campaign.state != 'archived') \
        .group_by(Campaign)

    impressions = query_template \
        .filter(AdLog.record_type == 'impr') \
        .all()
    for impr in impressions:
        campaign = impr[0]
        val = impr[1]
        mix[campaign.id].update({'id': campaign.id,
                                 'name': campaign.name,
                                 'state': funcs.states[campaign.state],
                                 'impr': val})

    clicks = query_template \
        .filter(AdLog.record_type == 'clck') \
        .all()
    for clck in clicks:
        campaign = clck[0]
        val = clck[1]
        mix[campaign.id].update({'campaign_id': campaign.id,
                                 'name': campaign.name,
                                 'state': funcs.states[campaign.state],
                                 'clck': val})
    data = mix.values()
    for d in data:
        try:
            d['ctr'] = '{0:0.02f}'.format(d['clck'] / d['impr'] * 100.0)
        except (ZeroDivisionError, TypeError, KeyError):
            d['ctr'] = '{0:0.02f}'.format(0.0)
        d['impr'] = funcs.format_decimal(d['impr'])
        d['clck'] = funcs.format_decimal(d['clck'])
    #if len(data) == 0:
    #    return ''
    return render_template('client/campaigns.html', data=data)


@client_bp.route("/creatives_by_campaign/<int:campaign_id>")
@login_required
def creatives_by_campaign(campaign_id):
    try:
        campaign = Campaign.query \
            .join(Organization.persons, Organization.campaigns) \
            .filter(Campaign.id == campaign_id,
                    Campaign.state != 'archived',
                    Person.id == current_user.person.id) \
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    creative_mix = defaultdict(dict)

    creatives_list = Creative.query \
        .join(Campaign.creatives) \
        .options(joinedload(Creative.creative_format)) \
        .filter(Campaign.id == campaign_id) \
        .all()
    for creative in creatives_list:
        creative_mix[creative.id].update({'campaign_id': creative.campaign.id,
                                         'creative_id': creative.id,
                                         'creative_name': creative.name,
                                         'creative_format': creative.creative_format,
                                         'frequency': creative.frequency,
                                         'target_impr': creative.target_impressions})

    if len(creatives_list) == 0:
        return render_template('client/no_creatives_yet.html',
                               campaign_name=campaign.name)

    query_template = session.query(Creative, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.id == campaign_id,
                Campaign.state != 'archived') \
        .group_by(Creative)

    impressions = query_template \
        .filter(AdLog.record_type == 'impr') \
        .all()
    for summary in impressions:
        creative = summary[0]
        val = summary[1]
        creative_mix[creative.id].update({'impr': val})

    clicks = query_template \
        .filter(AdLog.record_type == 'clck') \
        .all()
    for summary in clicks:
        creative = summary[0]
        val = summary[1]
        creative_mix[creative.id].update({'clck': val})

    creatives = creative_mix.values()
    for d in creatives:
        try:
            d['ctr'] = '{0:0.02f}'.format(d['clck'] / d['impr'] * 100.0)
        except TypeError:
            d['ctr'] = '{0:0.02f}'.format(0.0)
        except KeyError:
            d['ctr'] = u'нет'
        except ZeroDivisionError:
            d['ctr'] = '&infin;'
        try:
            reach = funcs.reach(d['target_impr'], d['impr'], d['frequency'])
            del d['frequency']
            d['reach'] = funcs.format_decimal('{0:0.0f}'.format(reach))
        except (ZeroDivisionError, TypeError):
            d['reach'] = '{0:0.0f}'.format(0.0)
        except KeyError:
            d['reach'] = u'нет'
        try:
            d['target_impr'] = funcs.format_decimal(d['target_impr'])
        except KeyError:
            pass
        try:
            d['impr'] = funcs.format_decimal(d['impr'])
        except KeyError:
            pass
        try:
            d['clck'] = funcs.format_decimal(d['clck'])
        except KeyError:
            pass

    enabled_sites = Site.query \
        .join(Campaign.sites) \
        .filter(Campaign.id == campaign_id,
                Site.is_hit == True) \
        .all()

    return render_template('client/creatives_by_campaign.html',
                           campaign=campaign,
                           creatives=creatives,
                           sites=enabled_sites)


@client_bp.route("/stats_by_campaign/<int:campaign_id>")
@login_required
def stats_by_campaign(campaign_id):
    try:
        campaign = Campaign.query \
            .join(Organization.persons, Organization.campaigns) \
            .filter(Campaign.id == campaign_id,
                    Person.id == current_user.person.id) \
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))
    return render_template('client/graph_by_campaign.html',
                           campaign=campaign)


@client_bp.route("/stats_graph_of_campaign_ajax/<int:campaign_id>", methods=["GET"])
@login_required
def stats_graph_of_campaign_ajax(campaign_id):
    campaign_query = Campaign.query \
        .filter(Campaign.id == campaign_id)
    if current_user.person.role == 'customer':
        campaign_query = campaign_query \
            .join(Organization.campaigns,
                  Organization.persons) \
            .filter(Person.id == current_user.person.id)
    try:
        campaign_query.one()
    except NoResultFound:
        return jsonify()

    query_template = session.query(func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.id == campaign_id,
                Campaign.state != 'archived')
    scale = request.args.get('scale', 'day')
    start_datetime = request.args.get('start_datetime', '01.01.1970 00:00')
    end_datetime = request.args.get('end_datetime', '01.01.1970 00:00')
    try:
        start_datetime = datetime.strptime(start_datetime, '%d.%m.%Y %H:%M')
        end_datetime = datetime.strptime(end_datetime, '%d.%m.%Y %H:%M')
    except ValueError:
        return jsonify()
    return jsonify(stats_prepare(query_template, start_datetime, end_datetime, scale))


@client_bp.route("/stats_by_creative/<int:creative_id>")
@login_required
def stats_by_creative(creative_id):
    try:
        creative = Creative.query \
            .join(Organization.persons,
                  Organization.campaigns) \
            .join(Campaign.creatives) \
            .options(joinedload(Creative.campaign)) \
            .filter(Creative.id == creative_id,
                    Person.id == current_user.person.id) \
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))
    return render_template('client/graph_by_creative.html',
                           creative=creative)


@client_bp.route("/stats_graph_of_creative_ajax/<int:creative_id>", methods=["GET"])
@login_required
def stats_graph_of_creative_ajax(creative_id):
    creative_query = Creative.query \
        .join(Campaign.creatives) \
        .filter(Creative.id == creative_id)
    if current_user.person.role == 'customer':
        creative_query = creative_query \
            .join(Campaign.organization,
                  Organization.persons) \
            .filter(Person.id == current_user.person.id)
    try:
        creative = creative_query.one()
    except NoResultFound:
        return jsonify()

    query_template = session.query(func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Creative.id == creative_id,
                Campaign.state != 'archived')
    scale = request.args.get('scale', 'day')
    start_datetime = request.args.get('start_datetime', '01.01.1970 00:00')
    end_datetime = request.args.get('end_datetime', '01.01.1970 00:00')
    try:
        start_datetime = datetime.strptime(start_datetime, '%d.%m.%Y %H:%M')
        end_datetime = datetime.strptime(end_datetime, '%d.%m.%Y %H:%M')
    except ValueError:
        return jsonify()
    return jsonify(stats_prepare(query_template,
                                 start_datetime,
                                 end_datetime,
                                 scale,
                                 creative.target_impressions,
                                 creative.frequency))


def stats_prepare(query_template, start_datetime, end_datetime, scale, target_impressions=None, frequency=None):
    res = {}

    total_impressions = query_template \
        .filter(AdLog.record_type == 'impr') \
        .one()[0]
    res['total-imprs'] = total_impressions if total_impressions else 0

    total_clicks = query_template \
        .filter(AdLog.record_type == 'clck') \
        .one()[0]
    res['total-clcks'] = total_clicks if total_clicks else 0

    try:
        res['total-ctr'] = '{0:0.02f}'.format(res['total-clcks'] / res['total-imprs'] * 100.0)
    except (ZeroDivisionError, TypeError):
        res['total-ctr'] = '{0:0.02f}'.format(0.0)

    if target_impressions is not None and frequency is not None:
        try:
            reach = funcs.reach(target_impressions, res['total-imprs'], frequency)
            res['total-reach'] = funcs.format_decimal('{0:0.0f}'.format(reach))
        except (ZeroDivisionError, TypeError):
            res['total-reach'] = '{0:0.0f}'.format(0.0)

    res['total-imprs'] = funcs.format_decimal(res['total-imprs'])
    res['total-clcks'] = funcs.format_decimal(res['total-clcks'])

    if scale == 'day':
        from_date = start_datetime.date()
        to_date = end_datetime.date()
        query_lego = query_template \
            .add_columns(AdLog.date_stamp) \
            .filter(AdLog.date_stamp >= from_date,
                    AdLog.date_stamp <= to_date) \
            .group_by(AdLog.date_stamp)

        impressions = query_lego \
            .filter(AdLog.record_type == 'impr') \
            .all()
        values = map(lambda x: x[0], impressions)
        # This is a some kind of bug because we keep and show AdLog.date_stamp as UTC (not local tz) based 'date' field.
        # In this case it doesn't matter I think.
        date_stamps = map(lambda x: timegm(x[1].timetuple()), impressions)
        res['impr'] = zip(date_stamps, values)

        clicks = query_lego \
            .filter(AdLog.record_type == 'clck') \
            .all()
        values = map(lambda x: x[0], clicks)
        # This is a some kind of bug because we keep and show AdLog.date_stamp as UTC (not local tz) based 'date' field.
        # In this case it doesn't matter I think.
        date_stamps = map(lambda x: timegm(x[1].timetuple()), clicks)
        res['clck'] = zip(date_stamps, values)

        res['bar-width'] = 86400    # bar width on plot = 1 day in seconds

    if scale == 'hour':
        query_lego = query_template \
            .add_columns(AdLog.date_to_hour_stamp) \
            .filter(AdLog.date_to_hour_stamp >= start_datetime,
                    AdLog.date_to_hour_stamp <= end_datetime) \
            .group_by(AdLog.date_to_hour_stamp)

        impressions = query_lego \
            .filter(AdLog.record_type == 'impr') \
            .all()
        values = map(lambda x: x[0], impressions)
        date_stamps = map(lambda x: timegm(utc_tz.localize(x[1]).astimezone(local_tz).timetuple()), impressions)
        res['impr'] = zip(date_stamps, values)

        clicks = query_lego \
            .filter(AdLog.record_type == 'clck') \
            .all()
        values = map(lambda x: x[0], clicks)
        date_stamps = map(lambda x: timegm(utc_tz.localize(x[1]).astimezone(local_tz).timetuple()), clicks)
        res['clck'] = zip(date_stamps, values)

        res['bar-width'] = 3600     # bar width on plot = 1 hour in seconds

    if scale == '5_mins':
        query_lego = query_template \
            .add_columns(AdLog.time_stamp) \
            .filter(AdLog.time_stamp >= start_datetime,
                    AdLog.time_stamp <= end_datetime) \
            .group_by(AdLog.time_stamp)

        impressions = query_lego \
            .filter(AdLog.record_type == 'impr') \
            .all()
        values = map(lambda x: x[0], impressions)
        date_stamps = map(lambda x: timegm(utc_tz.localize(x[1]).astimezone(local_tz).timetuple()), impressions)
        res['impr'] = zip(date_stamps, values)

        clicks = query_lego \
            .filter(AdLog.record_type == 'clck') \
            .all()
        values = map(lambda x: x[0], clicks)
        date_stamps = map(lambda x: timegm(utc_tz.localize(x[1]).astimezone(local_tz).timetuple()), clicks)
        res['clck'] = zip(date_stamps, values)

        res['bar-width'] = 300      # bar width on plot = 5 minutes in seconds

    return res
