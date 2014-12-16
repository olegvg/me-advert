# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'ogaidukov'

from collections import defaultdict
from io import BytesIO
from werkzeug import secure_filename
from flask import request, Blueprint, render_template, redirect, escape, jsonify, url_for, make_response
from flask.ext.login import login_required, logout_user, current_user
from console import app, login_manager, redirectors
from console.views import forms
from console.lib import funcs
from console.lib.identity import manager_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from commonlib.database import session
from commonlib.model import Campaign, Creative, CreativeFormat, GeoCountries, GeoCities, \
    Counter, AdLog, Person, Organization, Contractor, Site

manager_bp = Blueprint('manager', __name__)


@manager_bp.route("/organizations")
@login_required
@manager_required
def organizations():
    orgs = Organization.query \
        .options(joinedload(Organization.persons)) \
        .all()
    return render_template('manager/organizations.html',
                           orgs=orgs)


@manager_bp.route("/new_organization", methods=["GET", "POST"])
@login_required
@manager_required
def new_organization():
    form = forms.NewOrganizationForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        organization = Organization(form.name.data, form.full_name.data)
        session.add(organization)
        session.commit()
        return redirect(redirect_url)
    return render_template("manager/edit_organization.html",
                           form=form,
                           type='new',
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/edit_organization/<int:org_id>", methods=["GET", "POST"])
@login_required
@manager_required
def edit_organization(org_id):
    form = forms.EditOrganizationForm(request.form)
    organization = Organization.query.filter_by(id=org_id).first()
    if request.method == "POST" and form.validate_on_submit():
        organization.name = form.name.data
        organization.full_name = form.full_name.data
        session.commit()
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        return redirect(redirect_url)
    else:
        form.name.data = organization.name
        form.full_name.data = organization.full_name
    return render_template("manager/edit_organization.html",
                           form=form,
                           type='edit',
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/select_organizations_ajax", methods=["GET"])
@login_required
@manager_required
def select_organizations_ajax():
    def format_name(name, full_name):
        if full_name is None or full_name == u'':
            return u"{}".format(name)
        else:
            return u"{} ({})".format(name, full_name)

    query = escape(request.args.get('query'))
    like_arg = u"%{}%".format(query)
    organizations = Organization.query\
        .filter(or_(Organization.name.ilike(like_arg), Organization.full_name.ilike(like_arg))).all()
    res = map(lambda x: {'id': x.id, 'name': format_name(x.name, x.full_name)}, organizations)
    return jsonify(organizations=res)


@manager_bp.route("/organization_by_id_ajax", methods=["GET"])
@login_required
@manager_required
def organization_by_id_ajax():
    org_id = request.args.get('org_id')
    if org_id is not None and not org_id.isdigit():
        return jsonify()
    try:
        organization = Organization.query\
            .filter_by(id=org_id).one()
    except NoResultFound:
        return jsonify()
    if organization.full_name is None or organization.full_name == u'':
        name = u"{}".format(organization.name)
    else:
        name = u"{} ({})".format(organization.name, organization.full_name)
    return jsonify(id=organization.id, name=name)


@manager_bp.route("/persons")
@login_required
@manager_required
def persons():
    persons = Person.query \
        .options(joinedload(Person.organization)) \
        .all()
    return render_template('manager/persons.html',
                           persons=persons)


@manager_bp.route("/person/<int:person_id>")
@login_required
@manager_required
def person(person_id):
    persons = Person.query \
        .options(joinedload(Person.organization)) \
        .filter(Person.id == person_id) \
        .all()
    return render_template('manager/persons.html',
                           persons=persons)


@manager_bp.route("/new_person", methods=["GET", "POST"])
@login_required
@manager_required
def new_person():
    form = forms.NewPersonForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        person = Person(form.email.data, form.password.data, form.first_name.data, form.surname.data,
                        role=form.role.data, is_blocked=form.is_blocked.data)
        if form.role.data == 'customer':
            person.contractor_ref = None
            person.organization_ref = form.organization_id.data if form.organization_id.data else None
        elif form.role.data == 'contractor':
            person.contractor_ref = form.contractor_id.data if form.contractor_id.data else None
            person.organization_ref = None
        elif form.role.data == 'manager':
            person.contractor_ref = None
            person.organization_ref = None
        session.add(person)
        session.commit()
        return redirect(redirect_url)
    return render_template("manager/edit_person.html",
                           form=form,
                           type='new',
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/edit_person/<int:person_id>", methods=["GET", "POST"])
@login_required
@manager_required
def edit_person(person_id):
    form = forms.EditPersonForm(request.form)
    person = Person.query.filter_by(id=person_id).first()
    if request.method == "POST" and form.validate_on_submit():
        person.email = form.email.data
        person.first_name = form.first_name.data
        person.surname = form.surname.data
        if form.password.data != '******':
            person.update_password(form.password.data)
        person.organization_ref = form.organization_id.data if form.organization_id.data else None
        person.role = form.role.data
        if form.role.data == 'customer':
            person.contractor_ref = None
            person.organization_ref = form.organization_id.data if form.organization_id.data else None
        elif form.role.data == 'contractor':
            person.contractor_ref = form.contractor_id.data if form.contractor_id.data else None
            person.organization_ref = None
        elif form.role.data == 'manager':
            person.contractor_ref = None
            person.organization_ref = None
        person.is_blocked = form.is_blocked.data
        session.commit()
        if form.password.data != '******' and current_user.person.id == person_id:
            logout_user()
            redirect_url = url_for(login_manager.login_view)
        else:
            redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        return redirect(redirect_url)
    else:
        form.email.data = person.email
        form.first_name.data = person.first_name
        form.surname.data = person.surname
        form.password.data = '******'
        form.retry_password.data = '******'
        form.role.data = person.role
        form.organization_id.data = person.organization_ref
        form.contractor_id.data = person.contractor_ref
        form.is_blocked.data = person.is_blocked
    return render_template("manager/edit_person.html",
                           form=form,
                           type='edit',
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/campaigns_all")
@login_required
@manager_required
def campaigns_all():
    min_realstart_date_query = Campaign.query \
        .with_entities(Campaign.id, func.min(Counter.realstart_date).label('min_realstart_date')) \
        .join(Creative.counters) \
        .join(Creative.campaign) \
        .group_by(Campaign.id) \
        .subquery('min_realstart_date')
    campaigns_list = session.query(Campaign, 'min_realstart_date') \
        .options(joinedload(Campaign.organization)) \
        .outerjoin(min_realstart_date_query, min_realstart_date_query.c.id == Campaign.id) \
        .filter(Campaign.state != 'archived') \
        .all()

    impressions_summary = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'impr',
                Campaign.state != 'archived') \
        .group_by(Campaign) \
        .all()
    impressions_rej_geo = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'impr_rej_geo',
                Campaign.state != 'archived') \
        .group_by(Campaign) \
        .all()
    impressions_rej_browser = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'impr_rej_browser',
                Campaign.state != 'archived') \
        .group_by(Campaign) \
        .all()
    clicks_summary = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'clck',
                Campaign.state != 'archived') \
        .group_by(Campaign)\
        .all()
    clicks_rej_geo = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'clck_rej_geo',
                Campaign.state != 'archived') \
        .group_by(Campaign)\
        .all()
    clicks_rej_browser = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(AdLog.record_type == 'clck_rej_browser',
                Campaign.state != 'archived') \
        .group_by(Campaign)\
        .all()

    campaigns = prepare_campaigns(campaigns_list,
                                  impressions_summary,
                                  impressions_rej_geo,
                                  impressions_rej_browser,
                                  clicks_summary,
                                  clicks_rej_geo,
                                  clicks_rej_browser)
    return render_template('manager/campaigns/campaigns_all.html',
                           campaigns=campaigns)


@manager_bp.route("/campaigns_by_org/<int:org_id>")
@login_required
@manager_required
def campaigns_by_org(org_id):
    min_realstart_date_query = Campaign.query \
        .with_entities(Campaign.id, func.min(Counter.realstart_date).label('min_realstart_date')) \
        .join(Creative.counters) \
        .join(Creative.campaign) \
        .filter(Organization.id == org_id) \
        .group_by(Campaign.id) \
        .subquery('min_realstart_date')
    campaigns_list = session.query(Campaign, 'min_realstart_date') \
        .join(Campaign.organization) \
        .options(joinedload(Campaign.organization)) \
        .outerjoin(min_realstart_date_query, min_realstart_date_query.c.id == Campaign.id) \
        .filter(Organization.id == org_id,
                Campaign.state != 'archived') \
        .all()

    try:
        organization = campaigns_list[0]
        org_name = organization[0].organization.name
        org_full_name = organization[0].organization.full_name
    except IndexError:
        org = Organization.query.filter_by(id=org_id).one()
        return render_template('manager/campaigns/first_campaign.html',
                               org_name=org.name,
                               org_full_name=org.full_name)

    impressions_summary = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Organization.id == org_id,
                AdLog.record_type == 'impr',
                Campaign.state != 'archived') \
        .group_by(Campaign) \
        .all()
    impressions_rej_geo = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Organization.id == org_id,
                AdLog.record_type == 'impr_rej_geo',
                Campaign.state != 'archived') \
        .group_by(Campaign) \
        .all()
    impressions_rej_browser = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Organization.id == org_id,
                AdLog.record_type == 'impr_rej_browser',
                Campaign.state != 'archived') \
        .group_by(Campaign) \
        .all()
    clicks_summary = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Organization.id == org_id,
                AdLog.record_type == 'clck',
                Campaign.state != 'archived') \
        .group_by(Campaign)\
        .all()
    clicks_rej_geo = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Organization.id == org_id,
                AdLog.record_type == 'clck_rej_geo',
                Campaign.state != 'archived') \
        .group_by(Campaign)\
        .all()
    clicks_rej_browser = session.query(Campaign, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Organization.id == org_id,
                AdLog.record_type == 'clck_rej_browser',
                Campaign.state != 'archived') \
        .group_by(Campaign)\
        .all()

    campaigns = prepare_campaigns(campaigns_list,
                                  impressions_summary,
                                  impressions_rej_geo,
                                  impressions_rej_browser,
                                  clicks_summary,
                                  clicks_rej_geo,
                                  clicks_rej_browser)
    return render_template('manager/campaigns/campaigns_by_org.html',
                           campaigns=campaigns,
                           org_name=org_name,
                           org_full_name=org_full_name)


def prepare_campaigns(campaigns_list, impressions_summary, impressions_rej_geo, impressions_rej_browser,
                      clicks_summary, clicks_rej_geo, clicks_rej_browser):
    campaign_mix = defaultdict(dict)
    for campaign in campaigns_list:
        campaign_mix[campaign[0].id].update({'org_id': campaign[0].organization.id,
                                            'org_name': campaign[0].organization.name,
                                            'org_full_name': campaign[0].organization.full_name,
                                            'campaign_id': campaign[0].id,
                                            'campaign_name': campaign[0].name,
                                            'start_date': campaign[0].start_date,
                                            'realstart_date': campaign[1],
                                            'due_date': campaign[0].due_date,
                                            'state': funcs.states[campaign[0].state],
                                            'target_impr': campaign[0].target_impressions})

    for summary in impressions_summary:
        campaign = summary[0]
        val = summary[1]
        campaign_mix[campaign.id].update({'impr': val})
    for summary in impressions_rej_geo:
        campaign = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        campaign_mix[campaign.id].update({'impr_rej_geo': val})
    for summary in impressions_rej_browser:
        campaign = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        campaign_mix[campaign.id].update({'impr_rej_browser': val})

    for summary in clicks_summary:
        campaign = summary[0]
        val = summary[1]
        campaign_mix[campaign.id].update({'clck': val})
    for summary in clicks_rej_geo:
        campaign = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        campaign_mix[campaign.id].update({'clck_rej_geo': val})
    for summary in clicks_rej_browser:
        campaign = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        campaign_mix[campaign.id].update({'clck_browser': val})

    campaigns = campaign_mix.values()
    for d in campaigns:
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
            d['reach'] = funcs.format_decimal('{0:0.0f}'.format(reach))
        except (ZeroDivisionError, TypeError):
            d['reach'] = '{0:0.0f}'.format(0.0)
        except KeyError:
            d['reach'] = u'нет'
        try:
            if d['target_impr']:
                d['target_impr'] = funcs.format_decimal(d['target_impr'])
            else:
                d['target_impr'] = u'нет'
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

    return campaigns


@manager_bp.route("/stats_by_campaign/<int:campaign_id>")
@login_required
@manager_required
def stats_by_campaign(campaign_id):
    campaign = Campaign.query\
        .options(joinedload(Campaign.organization)) \
        .filter(Campaign.id == campaign_id) \
        .one()
    if campaign is None:
        return redirect(url_for(redirectors[current_user.person.role]))
    return render_template('manager/campaigns/graph_by_campaign.html',
                           start_date=campaign.start_date,
                           due_date=campaign.due_date,
                           campaign=campaign)


@manager_bp.route("/stats_by_creative/<int:creative_id>")
@login_required
@manager_required
def stats_by_creative(creative_id):
    creative = Creative.query \
        .options(joinedload(Creative.campaign, Campaign.organization)) \
        .filter(Creative.id == creative_id) \
        .one()
    if creative is None:
        return redirect(url_for(redirectors[current_user.person.role]))
    return render_template('manager/campaigns/graph_by_creative.html',
                           creative=creative)


@manager_bp.route("/new_campaign", methods=["GET", "POST"])
@login_required
@manager_required
def new_campaign():
    form = forms.NewCampaignForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        campaign = Campaign(form.name.data, None, form.start_date.data, form.due_date.data,
                            state=form.state.data,
                            target_impressions=form.target_impressions.data)
        campaign.organization_ref = form.organization_id.data
        campaign.sites = Site.to_list(form.sites.data)
        session.add(campaign)
        session.commit()
        return redirect(redirect_url)
    return render_template("manager/campaigns/edit_campaign.html",
                           form=form,
                           type='new',
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/edit_campaign/<int:campaign_id>", methods=["GET", "POST"])
@login_required
@manager_required
def edit_campaign(campaign_id):
    try:
        campaign = session.query(Campaign) \
            .options(joinedload(Campaign.organization)) \
            .filter(Campaign.id == campaign_id,
                    Campaign.state != 'archived')\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    form = forms.EditCampaignForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        campaign.name = form.name.data
        campaign.organization_ref = form.organization_id.data
        campaign.start_date = form.start_date.data
        campaign.due_date = form.due_date.data
        campaign.state = form.state.data
        campaign.target_impressions = form.target_impressions.data
        if form.is_archived.data is True:
            campaign.state = 'archived'
        campaign.sites.extend(Site.to_list(form.sites.data))
        session.commit()
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        return redirect(redirect_url)
    else:
        form.name.data = campaign.name
        form.organization_id.data = campaign.organization_ref
        form.start_date.data = campaign.start_date
        form.due_date.data = campaign.due_date
        form.state.data = campaign.state
        form.target_impressions.data = campaign.target_impressions
        form.is_archived.data = True if campaign.state == 'archived' else False
        form.sites.data = ""
    return render_template("manager/campaigns/edit_campaign.html",
                           campaign=campaign,
                           form=form,
                           type='edit',
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/creatives_by_campaign/<int:campaign_id>")
@login_required
@manager_required
def creatives_by_campaign(campaign_id):
    try:
        campaign = session.query(Campaign) \
            .options(joinedload(Campaign.organization)) \
            .filter(Campaign.id == campaign_id,
                    Campaign.state != 'archived')\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    creatives_list = Creative.query \
        .join(Campaign.creatives) \
        .options(joinedload(Creative.creative_format)) \
        .filter(Campaign.id == campaign_id) \
        .all()

    realstart_date = session.query(func.min(Counter.realstart_date)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .filter(Campaign.id == campaign_id) \
        .one()[0]

    if len(creatives_list) == 0:
        return render_template('manager/campaigns/first_creative.html',
                               org_id=campaign.organization.id,
                               org_name=campaign.organization.name,
                               org_full_name=campaign.organization.full_name,
                               campaign_id=campaign_id,
                               campaign_name=campaign.name)

    impressions_summary = session.query(Creative, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.id == campaign_id,
                AdLog.record_type == 'impr') \
        .group_by(Creative) \
        .all()
    impressions_rej_geo = session.query(Creative, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.id == campaign_id,
                AdLog.record_type == 'impr_rej_geo') \
        .group_by(Creative) \
        .all()
    impressions_rej_browser = session.query(Creative, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.id == campaign_id,
                AdLog.record_type == 'impr_rej_browser') \
        .group_by(Creative) \
        .all()
    clicks_summary = session.query(Creative, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.id == campaign_id,
                AdLog.record_type == 'clck') \
        .group_by(Creative)\
        .all()
    clicks_rej_geo = session.query(Creative, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.id == campaign_id,
                AdLog.record_type == 'clck_rej_geo') \
        .group_by(Creative)\
        .all()
    clicks_rej_browser = session.query(Creative, func.sum(AdLog.value)) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .filter(Campaign.id == campaign_id,
                AdLog.record_type == 'clck_rej_browser') \
        .group_by(Creative)\
        .all()

    creative_mix = defaultdict(dict)
    for creative in creatives_list:
        creative_mix[creative.id].update({'creative_id': creative.id,
                                         'creative_format': creative.creative_format,
                                         'start_date': campaign.start_date,
                                         'realstart_date': realstart_date,
                                         'due_date': campaign.due_date,
                                         'name': creative.name,
                                         'frequency': creative.frequency,
                                         'target_impr': creative.target_impressions,
                                         'geo_cities': creative.geo_cities if creative.geo_countries else [],
                                         'geo_countries': creative.geo_countries if creative.geo_countries else []})

    for summary in impressions_summary:
        creative = summary[0]
        val = summary[1]
        creative_mix[creative.id].update({'impr': val})
    for summary in impressions_rej_geo:
        creative = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        creative_mix[creative.id].update({'impr_rej_geo': val})
    for summary in impressions_rej_browser:
        creative = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        creative_mix[creative.id].update({'impr_rej_browser': val})

    for summary in clicks_summary:
        creative = summary[0]
        val = summary[1]
        creative_mix[creative.id].update({'clck': val})
    for summary in clicks_rej_geo:
        creative = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        creative_mix[creative.id].update({'clck_rej_geo': val})
    for summary in clicks_rej_browser:
        creative = summary[0]
        try:
            val = funcs.format_decimal(summary[1])
        except KeyError:
            continue
        creative_mix[creative.id].update({'clck_rej_browser': val})

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

    return render_template('manager/campaigns/creatives_by_campaign.html',
                           creatives=creatives,
                           org_id=campaign.organization.id,
                           org_name=campaign.organization.name,
                           org_full_name=campaign.organization.full_name,
                           campaign_id=campaign.id,
                           campaign_name=campaign.name)


@manager_bp.route("/new_creative_to_campaign/<int:campaign_id>", methods=["GET", "POST"])
@login_required
@manager_required
def new_creative_to_campaign(campaign_id):
    try:
        campaign = session.query(Campaign) \
            .options(joinedload(Campaign.organization)) \
            .filter(Campaign.id == campaign_id,
                    Campaign.state != 'archived')\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    form = forms.CreativeForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        creative = Creative(campaign, None, form.name.data, form.frequency.data, form.target_impressions.data,
                            form.click_target_url.data, form.impression_target_url.data,
                            form.geo_cities.data.split(','), form.geo_countries.data.split(','))
        creative.creative_format_ref = form.creative_format_id.data
        session.add(campaign)
        session.commit()
        return redirect(redirect_url)
    return render_template("manager/campaigns/edit_creative.html",
                           campaign=campaign,
                           form=form,
                           type='new',
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/edit_creative/<int:creative_id>", methods=["GET", "POST"])
@login_required
@manager_required
def edit_creative(creative_id):
    try:
        creative = Creative.query \
            .join(Campaign.creatives) \
            .options(joinedload(Creative.campaign)) \
            .filter(Creative.id == creative_id,
                    Campaign.state != 'archived')\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    form = forms.CreativeForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        creative.creative_format_ref = form.creative_format_id.data
        creative.name = form.name.data
        creative.frequency = form.frequency.data
        creative.target_impressions = form.target_impressions.data
        creative.click_target_url = form.click_target_url.data
        creative.impression_target_url = form.impression_target_url.data
        creative.geo_cities = form.geo_cities.data.split(',')
        creative.geo_countries = form.geo_countries.data.split(',')
        session.commit()
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        return redirect(redirect_url)
    else:
        form.creative_format_id.data = creative.creative_format_ref
        form.name.data = creative.name
        form.frequency.data = creative.frequency
        form.target_impressions.data = creative.target_impressions
        form.click_target_url.data = creative.click_target_url
        form.impression_target_url.data = creative.impression_target_url
        form.geo_countries.data = ','.join(creative.geo_countries) if creative.geo_countries else ''
        form.geo_cities.data = ','.join(creative.geo_cities) if creative.geo_cities else ''
    return render_template("manager/campaigns/edit_creative.html",
                           campaign=creative.campaign,
                           form=form,
                           type='edit',
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/select_creative_formats_ajax", methods=["GET"])
@login_required
@manager_required
def select_creative_formats_ajax():
    query = escape(request.args.get('query'))

    like_arg = u"%{}%".format(query)
    creative_formats = CreativeFormat.query\
        .filter(or_(CreativeFormat.format_name.ilike(like_arg),
                    CreativeFormat.dimension_x.ilike(like_arg),
                    CreativeFormat.dimension_y.ilike(like_arg))) \
        .all()
    res = map(lambda x: {'id': x.id, 'name': x.get_full_name()}, creative_formats)
    return jsonify(creative_formats=res)


@manager_bp.route("/creative_format_by_id_ajax", methods=["GET"])
@login_required
@manager_required
def creative_format_by_id_ajax():
    creative_format_id = request.args.get('creative_format_id')
    if creative_format_id is not None and not creative_format_id.isdigit():
        return jsonify()
    try:
        creative_format = CreativeFormat.query \
            .filter_by(id=creative_format_id) \
            .one()
    except NoResultFound:
        return jsonify()

    return jsonify(id=creative_format.id, name=creative_format.get_full_name())


@manager_bp.route("/select_geo_counties_by_mask_ajax", methods=["GET"])
@login_required
@manager_required
def select_geo_counties_by_mask_ajax():
    query = escape(request.args.get('query'))

    like_arg = u"%{}%".format(query)
    countries = GeoCountries.query\
        .filter(GeoCountries.country_full_name.ilike(like_arg))\
        .all()
    res = map(lambda x: {'id': x.country_iso_id, 'name': x.country_full_name}, countries)
    return jsonify(geo_countries=res)


@manager_bp.route("/geo_country_by_id_ajax", methods=["GET"])
@login_required
@manager_required
def geo_country_by_id_ajax():
    geo_country_id = request.args.get('geo_country_id')
    geo_countries = geo_country_id.split(',')
    try:
        geo_countries_objs = GeoCountries.query \
            .filter(GeoCountries.country_iso_id.in_(geo_countries)) \
            .all()
    except NoResultFound:
        return jsonify()
    res = map(lambda x: {'id': x.country_iso_id, 'name': x.country_full_name}, geo_countries_objs)
    return jsonify(geo_countries=res)


@manager_bp.route("/select_geo_cities_by_mask_ajax", methods=["GET"])
@login_required
@manager_required
def select_geo_cities_by_mask_ajax():
    query = escape(request.args.get('query'))

    like_arg = u"%{}%".format(query)
    cities = GeoCities.query\
        .filter(GeoCities.city_name.ilike(like_arg))\
        .all()
    res = map(lambda x: {'id': x.city_name, 'name': x.city_name}, cities)
    return jsonify(geo_cities=res)


@manager_bp.route("/counters_by_creative/<int:creative_id>")
@login_required
@manager_required
def counters_by_creative(creative_id):
    try:
        creative = Creative.query \
            .join(Campaign.creatives) \
            .options(joinedload(Creative.campaign, Campaign.organization),
                     joinedload(Creative.creative_format)) \
            .filter(Creative.id == creative_id,
                    Campaign.state != 'archived') \
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    counter_impressions = session.query(Counter, Contractor.name, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .join(Counter.contractor) \
        .filter(Creative.id == creative_id,
                AdLog.record_type == 'impr') \
        .group_by(Counter, Contractor.name)\
        .all()
    counter_impressions_rej_geo = session.query(Counter, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .join(Counter.contractor) \
        .filter(Creative.id == creative_id,
                AdLog.record_type == 'impr_rej_geo') \
        .group_by(Counter)\
        .all()
    counter_impressions_rej_browser = session.query(Counter, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .join(Counter.contractor) \
        .filter(Creative.id == creative_id,
                AdLog.record_type == 'impr_rej_browser') \
        .group_by(Counter)\
        .all()
    counter_clicks = session.query(Counter, Contractor.name, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .join(Counter.contractor) \
        .filter(Creative.id == creative_id,
                AdLog.record_type == 'clck') \
        .group_by(Counter, Contractor.name)\
        .all()
    counter_clicks_rej_geo = session.query(Counter, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .join(Counter.contractor) \
        .filter(Creative.id == creative_id,
                AdLog.record_type == 'clck_rej_geo') \
        .group_by(Counter)\
        .all()
    counter_clicks_rej_browser = session.query(Counter, func.sum(AdLog.value)) \
        .join(Organization.campaigns) \
        .join(Campaign.creatives) \
        .join(Creative.counters) \
        .join(Counter.logs) \
        .join(Counter.contractor) \
        .filter(Creative.id == creative_id,
                AdLog.record_type == 'clck_rej_browser') \
        .group_by(Counter)\
        .all()

    # TODO rewrite this shit!
    counter_mix = defaultdict(dict)
    for impr in counter_impressions:
        counter = impr[0]
        contractor_name = impr[1]
        val = impr[2]
        counter_mix[counter.id].update({'counter_id': counter.id,
                                        'counter_description': counter.description,
                                        'contractor_name': contractor_name,
                                        'realstart_date': counter.realstart_date,
                                        'due_date': creative.campaign.due_date,
                                        'mu_ctr': counter.mu_ctr,
                                        'sigma_ctr': counter.sigma_ctr,
                                        'banner_types': counter.banner_types,
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
        contractor_name = clck[1]
        val = clck[2]
        counter_mix[counter.id].update({'counter_id': counter.id,
                                        'contractor_name': contractor_name,
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

    if len(counters) == 0:
        return render_template('manager/campaigns/first_counter.html',
                               creative=creative)
    else:
        return render_template('manager/campaigns/counters.html',
                               counters=counters,
                               creative=creative)


@manager_bp.route("/counters_details_by_creative/<int:creative_id>")
@login_required
@manager_required
def counters_details_by_creative(creative_id):
    try:
        creative = Creative.query \
            .options(joinedload(Creative.campaign, Campaign.organization)) \
            .filter(Creative.id == creative_id)\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    counters = Counter.query \
        .join(Counter.creative) \
        .join(Counter.logs) \
        .options(joinedload(Counter.contractor),
                 joinedload(Counter.creative,
                            Creative.campaign,
                            Campaign.organization)) \
        .filter(Creative.id == creative_id) \
        .all()
    if len(counters) == 0:
        return render_template('manager/campaigns/counters_details_empty.html',
                               creative=creative)

    org_name = creative.campaign.organization.name
    org_full_name = creative.campaign.organization.full_name
    campaign_name = creative.campaign.name

    ads_base = app.config['ROTABANNER_URL_BASE'].rstrip('/')
    return render_template('manager/campaigns/counters_details.html',
                           counters=counters,
                           creative=creative,
                           ads_base=ads_base,
                           org_name=org_name,
                           org_full_name=org_full_name,
                           campaign_name=campaign_name)


@manager_bp.route("/one_counter_details/<int:counter_id>")
@login_required
@manager_required
def one_counter_details(counter_id):
    try:
        counter = Counter.query \
            .options(joinedload(Counter.contractor),
                     joinedload(Counter.creative,
                                Creative.campaign,
                                Campaign.organization)) \
            .filter(Counter.id == counter_id)\
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    org_name = counter.creative.campaign.organization.name
    org_full_name = counter.creative.campaign.organization.full_name
    campaign_name = counter.creative.campaign.name

    ads_base = app.config['ROTABANNER_URL_BASE'].rstrip('/')
    return render_template('manager/campaigns/one_counter_details.html',
                           counter=counter,
                           creative=counter.creative,
                           ads_base=ads_base,
                           org_name=org_name,
                           org_full_name=org_full_name,
                           campaign_name=campaign_name)


@manager_bp.route("/swf_by_counter/<int:counter_id>", methods=["GET", "POST"])
@login_required
@manager_required
def swf_by_counter(counter_id):
    counter = Counter.query \
        .filter(Counter.id == counter_id)\
        .one()
    if counter.creative_file_swf is None:
        return ""
    resp = make_response(counter.creative_file_swf)
    resp.headers['Content-Type'] = "application/x-shockwave-flash"
    return resp


@manager_bp.route("/gif_by_counter/<int:counter_id>", methods=["GET", "POST"])
@login_required
@manager_required
def gif_by_counter(counter_id):
    counter = Counter.query \
        .filter(Counter.id == counter_id)\
        .one()
    if counter.creative_file_gif is None:
        return ""

    extension = counter.creative_file_extension
    try:
        mime_type = {'gif': 'image/gif', 'jpg': 'image/jpeg'}[extension]
    except KeyError:
        return ''
    resp = make_response(counter.creative_file_gif)
    resp.headers['Content-Type'] = mime_type
    return resp


@manager_bp.route("/new_counter_to_creative/<int:creative_id>", methods=["GET", "POST"])
@login_required
@manager_required
def new_counter_to_creative(creative_id):
    try:
        creative = Creative.query \
            .join(Campaign.creatives) \
            .options(joinedload(Creative.campaign, Campaign.organization),
                     joinedload(Creative.creative_format)) \
            .filter(Creative.id == creative_id,
                    Campaign.state != 'archived') \
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    form = forms.CounterForm()
    if request.method == "POST" and form.validate_on_submit():
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        try:
            mu_ctr = float(form.mu_ctr.data)
            sigma_ctr = float(form.sigma_ctr.data)
        except (ValueError, TypeError):
            mu_ctr = None
            sigma_ctr = None
        counter = Counter(creative,
                          None,
                          mu_ctr=mu_ctr,
                          sigma_ctr=sigma_ctr,
                          description=form.description.data)
        counter.contractor_ref = form.contractor_id.data
        if form.creative_file_swf.has_file():
            counter.creative_filename_swf = secure_filename(form.creative_file_swf.data.filename)
            swf_file_object = BytesIO()
            form.creative_file_swf.data.save(swf_file_object)
            counter.creative_file_swf = swf_file_object.getvalue()
            swf_file_object.close()
        if form.creative_file_gif.has_file():
            counter.creative_filename_gif = secure_filename(form.creative_file_gif.data.filename)
            gif_file_object = BytesIO()
            form.creative_file_gif.data.save(gif_file_object)
            counter.creative_file_gif = gif_file_object.getvalue()
            gif_file_object.close()
        impr_log_record = AdLog(counter, 'impr', None, 0)
        clck_log_record = AdLog(counter, 'clck', None, 0)
        session.add_all([counter, impr_log_record, clck_log_record])
        session.commit()
        return redirect(redirect_url)
    return render_template("manager/edit_counter.html",
                           form=form,
                           type='new',
                           creative=creative,
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/edit_counter/<int:counter_id>", methods=["GET", "POST"])
@login_required
@manager_required
def edit_counter(counter_id):
    try:
        creative = Creative.query \
            .join(Creative.counters) \
            .options(joinedload(Creative.campaign, Campaign.organization),
                     joinedload(Creative.creative_format)) \
            .filter(Counter.id == counter_id,
                    Campaign.state != 'archived') \
            .one()
    except NoResultFound:
        return redirect(url_for(redirectors[current_user.person.role]))

    # forms.CounterForm(request.form) is incorrect for Flask-WTF & file uploads because Flask-WTF's constructor
    # automatically handles request.files
    form = forms.CounterForm()
    counter = Counter.query.filter_by(id=counter_id).first()
    if request.method == "POST" and form.validate_on_submit():
        counter.contractor_ref = form.contractor_id.data
        try:
            counter.mu_ctr = float(form.mu_ctr.data)
            counter.sigma_ctr = float(form.sigma_ctr.data)
        except (ValueError, TypeError):
            counter.mu_ctr = None
            counter.sigma_ctr = None
        if form.creative_file_swf.has_file():
            counter.creative_filename_swf = secure_filename(form.creative_file_swf.data.filename)
            swf_file_object = BytesIO()
            form.creative_file_swf.data.save(swf_file_object)
            counter.creative_file_swf = swf_file_object.getvalue()
            swf_file_object.close()
        if form.creative_file_gif.has_file():
            counter.creative_filename_gif = secure_filename(form.creative_file_gif.data.filename)
            gif_file_object = BytesIO()
            form.creative_file_gif.data.save(gif_file_object)
            counter.creative_file_gif = gif_file_object.getvalue()
            gif_file_object.close()
        counter.description = form.description.data
        session.commit()
        redirect_url = request.args.get('back_url', url_for(redirectors[current_user.person.role]))
        return redirect(redirect_url)
    else:
        form.contractor_id.data = counter.contractor_ref
        form.mu_ctr.data = counter.mu_ctr
        form.sigma_ctr.data = counter.sigma_ctr

        # object.filename is my own custom field needs to carry out filename of file stored in DB
        form.creative_file_swf.filename = counter.creative_filename_swf
        form.creative_file_gif.filename = counter.creative_filename_gif
        form.description.data = counter.description
    return render_template("manager/edit_counter.html",
                           form=form,
                           type='edit',
                           creative=creative,
                           back_url=request.referrer if request.referrer else None)


@manager_bp.route("/select_contractors_ajax", methods=["GET"])
@login_required
@manager_required
def select_contractors_ajax():
    query = escape(request.args.get('query'))
    like_arg = u"%{}%".format(query)
    contractors = Contractor.query \
        .filter(or_(Contractor.name.ilike(like_arg),
                    Contractor.full_name.ilike(like_arg))) \
        .all()
    res = []
    for contractor in contractors:
        if contractor.full_name:
            row = {'id': contractor.id, 'name': u"{} ({})".format(contractor.name, contractor.full_name)}
        else:
            row = {'id': contractor.id, 'name': u"{}".format(contractor.name)}
        res.append(row)
    return jsonify(contractors=res)


@manager_bp.route("/contractor_by_id_ajax", methods=["GET"])
@login_required
@manager_required
def contractor_by_id_ajax():
    contractor_id = request.args.get('contractor_id')
    if contractor_id is not None and not contractor_id.isdigit():
        return jsonify()
    try:
        contractor = Contractor.query \
            .filter_by(id=contractor_id).one()
    except NoResultFound:
        return jsonify()
    if contractor.full_name:
        name = u"{} ({})".format(contractor.name, contractor.full_name)
    else:
        name = u"{}".format(contractor.name)

    return jsonify(id=contractor.id, name=name)


@manager_bp.route("/contractors", defaults={'contractor_id': None}, methods=["GET"])
@manager_bp.route("/contractors/<int:contractor_id>", methods=["GET"])
@login_required
@manager_required
def contractors(contractor_id):
    all_contractors = Contractor.query.all()
    try:
        contractor = Contractor.query \
            .options(joinedload(Contractor.counters,
                                Counter.creative,
                                Creative.campaign,
                                Campaign.organization)) \
            .filter(Contractor.id == contractor_id) \
            .one()
    except NoResultFound:
        return render_template('manager/contractors.html',
                               counters=[],
                               all_contractors=all_contractors,
                               contractor=None)

    def query_template(query_obj):
        return query_obj \
            .join(Organization.campaigns) \
            .join(Campaign.creatives) \
            .join(Creative.counters) \
            .join(Counter.logs) \
            .join(Counter.contractor) \
            .filter(Contractor.id == contractor_id)

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
                                        'start_date': counter.creative.campaign.start_date,
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

    return render_template('manager/contractors.html',
                           counters=counters,
                           all_contractors=all_contractors,
                           contractor=contractor)
