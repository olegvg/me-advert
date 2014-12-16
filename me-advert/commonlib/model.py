# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

import hashlib
import re
from os import urandom
import datetime

from sqlalchemy import Column, Integer, ForeignKey, String, Unicode, UnicodeText, \
    Boolean, Enum, DateTime, Date, Float
from sqlalchemy.dialects.postgres import ARRAY, BYTEA
from sqlalchemy.orm import relationship, validates
from sqlalchemy.orm.exc import NoResultFound
from commonlib import database

# TODO Make a __repr__ for each class


class DBVersion(database.Base):
    __tablename__ = 'storage_version'

    id = Column(Integer, primary_key=True)
    version_serial = Column(Integer, unique=True)
    version_string = Column(Unicode(128))


class Organization(database.Base):
    __tablename__ = 'organizations'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(128), unique=True)            # Short name of a customer organisation
    full_name = Column(Unicode(512))                    # Long name of a customer organisation
    # 'campaigns' column backref'ed from 'Campaign'
    # 'persons' column backref'ed from 'Person'
    description = Column(UnicodeText)

    def __init__(self, name, full_name=None, description=None):
        self.name = name
        self.full_name = full_name
        self.description = description


class Person(database.Base):
    __tablename__ = 'persons'

    id = Column(Integer, primary_key=True)
    email = Column(Unicode(128), unique=True, index=True)
    password = Column(String(128))                      # Salted hash of password, fitted to SHA512
    first_name = Column(Unicode(128))
    surname = Column(Unicode(128))
    organization_ref = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'))
    contractor_ref = Column(Integer, ForeignKey('contractors.id'))
    organization = relationship("Organization", backref='persons', cascade="all")
    contractor = relationship("Contractor", backref='persons', cascade="all")
    salt = Column(String(128))                          # Crypto salt for password, fitted to SHA512
    role = Column(Enum('manager',
                       'customer',
                       'contractor',
                       name='person_role_type'), index=True)
    is_blocked = Column(Boolean, index=True)            # disables login completely
    description = Column(UnicodeText)

    def __init__(self, email, plain_password, first_name, surname, organization=None, contractor=None,
                 role='customer', is_blocked=False, description=None):
        self.email = email
        self.update_password(plain_password)
        self.first_name = first_name
        self.surname = surname
        self.organization = organization
        self.contractor = contractor
        self.role = role
        self.is_blocked = is_blocked
        self.description = description

    def update_password(self, plain_password):
        self.salt = hashlib.sha256(urandom(32)).hexdigest()     # potentially DDoSable point because of urandom
        self.password = hashlib.sha256(self.salt + plain_password).hexdigest()

    def check_password(self, plain_password):
        return hashlib.sha256(self.salt + plain_password).hexdigest() == self.password


class Campaign(database.Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    organization_ref = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'))
    name = Column(Unicode(128), unique=True)            # Descriptive short name of campaign
    organization = relationship("Organization", backref='campaigns', cascade="all")
    start_date = Column(Date)
    due_date = Column(Date)
    state = Column(Enum('active', 'paused', 'completed', 'archived', name='campaign_state'), index=True)
    # 'counters' column backref'ed from 'Counter'
    # 'dispenser' column backref'ed from 'Dispenser'
    target_impressions = Column(Integer)                # Total target impressions in scope of campaign
    description = Column(UnicodeText)
    # 'creatives' column backref'ed from 'Creative'
    # 'sites' column backref'ed from 'Site'

    def __init__(self, name, organization, start_date, due_date, state='paused',
                 target_impressions=0, description=None):
        self.name = name
        self.organization = organization
        self.start_date = start_date if start_date else datetime.date.today()
        self.due_date = due_date
        self.state = state
        self.target_impressions = target_impressions
        self.description = description


class CreativeFormat(database.Base):
    __tablename__ = 'creative_formats'

    id = Column(Integer, primary_key=True)
    format_name = Column(Unicode(128))
    dimension_x = Column(Unicode(6))
    dimension_y = Column(Unicode(6))
    # 'creatives' column backref'ed from 'Creative'

    def __init__(self, format_name, dimension_x, dimension_y):
        self.format_name = format_name
        self.dimension_x = dimension_x
        self.dimension_y = dimension_y

    def get_full_name(self):
        return u"{} {}x{}".format(self.format_name, self.dimension_x, self.dimension_y)

    @property
    def are_dimensions_int(self):
        try:
            int(self.dimension_x)
            int(self.dimension_y)
            return True
        except ValueError:
            return False


class Site(database.Base):
    __tablename__ = 'sites'

    id = Column(Integer, primary_key=True)
    campaign_ref = Column(Integer, ForeignKey('campaigns.id', ondelete='CASCADE'), index=True)
    campaign = relationship("Campaign", backref='sites', cascade="all")
    site = Column(UnicodeText)
    is_hit = Column(Boolean, default=False, index=True)

    def __init__(self, site):
        self.site = site

    @classmethod
    def to_list(cls, sites):
        return [Site(site) for site in re.split('\s', sites) if site != '']


class Creative(database.Base):
    __tablename__ = 'creatives'

    id = Column(Integer, primary_key=True)
    campaign_ref = Column(Integer, ForeignKey('campaigns.id', ondelete='CASCADE'), index=True)
    creative_format_ref = Column(Integer, ForeignKey('creative_formats.id', ondelete='CASCADE'), index=True)
    campaign = relationship("Campaign", backref='creatives', cascade="all")
    creative_format = relationship("CreativeFormat", backref='creatives', cascade="all")
    name = Column(Unicode(128))
    # 'counters' column backref'ed from 'Counter'
    frequency = Column(Float)                           # Special advertising term.
                                                        # See http://en.wikipedia.org/wiki/Effective_frequency
    target_impressions = Column(Integer)                # Total target impressions in scope of creative
    click_target_url = Column(UnicodeText())            # Click URL redirects to.
    impression_target_url = Column(UnicodeText())       # Impression URL redirects to.
    geo_cities = Column(ARRAY(UnicodeText))
    geo_countries = Column(ARRAY(UnicodeText))

    def __init__(self, campaign, creative_format, name, frequency, target_impressions,
                 click_target_url, impression_target_url=None, geo_cities=None, geo_countries=None):
        self.campaign = campaign
        self.creative_format = creative_format
        self.name = name
        self.frequency = frequency
        self.target_impressions = target_impressions
        self.click_target_url = click_target_url
        self.impression_target_url = impression_target_url
        self.geo_cities = geo_cities
        self.geo_countries = geo_countries

    @validates('impression_target_url', 'click_target_url', 'geo_cities',
               'geo_countries', 'creative_format', 'creative_format_ref')
    def rotabanner_target_urls_invalidate(self, key, val):
        if val != getattr(self, key) and database.redisdb is not None:
            for counter in self.counters:
                database.redisdb.delete('counter-{}'.format(counter.uniq_id))
        return val


class Contractor(database.Base):
    # TODO It'd better move data from this table to 'Organization' (with 'is_contractor' field set to 'True')
    __tablename__ = 'contractors'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(128), unique=True)            # Short name of a contractor organisation
    full_name = Column(Unicode(512))                    # Long name of a contractor organisation
    # 'counters' column backref'ed from 'Counter'
    # 'persons' column backref'ed from 'Person'
    description = Column(UnicodeText)

    def __init__(self, name, full_name=None, description=None):
        self.name = name
        self.full_name = full_name
        self.description = description


class Counter(database.Base):
    __tablename__ = 'counters'

    id = Column(Integer, primary_key=True)
    creative_ref = Column(Integer, ForeignKey('creatives.id', ondelete='CASCADE'), index=True)
    contractor_ref = Column(Integer, ForeignKey('contractors.id', ondelete='CASCADE'), index=True)
    creative = relationship("Creative", backref='counters', cascade="all")
    contractor = relationship("Contractor", backref='counters', cascade="all")
    uniq_id = Column(String(64), unique=True, index=True)   # Unique id of counter, fitted to SHA256
    mu_ctr = Column(Float)
    sigma_ctr = Column(Float)
    realstart_date = Column(Date)
    creative_file_swf = Column(BYTEA)
    creative_filename_swf = Column(UnicodeText)
    creative_file_gif = Column(BYTEA)
    creative_filename_gif = Column(UnicodeText)
    # 'logs' column backref'ed from 'AdLog'
    # 'banner_distr_status' column backref'ed from BannerDistStatus
    description = Column(UnicodeText)

    def __init__(self, creative, contractor, uniq_id=None, mu_ctr=None, sigma_ctr=None, description=None):
        self.creative = creative
        self.contractor = contractor
        self.uniq_id = uniq_id if uniq_id else hashlib.sha256(urandom(32)).hexdigest()
        self.mu_ctr = mu_ctr
        self.sigma_ctr = sigma_ctr
        self.description = description

    @validates('mu_ctr', 'sigma_ctr')
    def rotabanner_ctrs_invalidate(self, key, val):
        if val != getattr(self, key) and database.redisdb is not None:
            database.redisdb.delete('counter-{}'.format(self.uniq_id))
        return val

    @validates('creative_file_swf', 'creative_file_gif')
    def upload_to_cdn(self, key, val):
        if database.redisdb is not None:
            database.redisdb.delete('counter-{}'.format(self.uniq_id))
        return val

    @property
    def creative_file_extension(self):
        """
        It's a strange property which returns extension (now it is either 'gif' or 'jpg' or None) of
        supplementary creative stored at fields 'creative_file_gif' and 'creative_filename_gif'
        """
        try:
            extension = self.creative_filename_gif.rsplit(u'.', 1)[-1]
        except AttributeError:
            return None
        if extension in (u'jpg', u'gif'):
            return extension
        else:
            return None

    @property
    def banner_types(self):
        try:
            first = 'swf' if self.creative_filename_swf.rsplit(u'.', 1)[-1] == u'swf' else None
        except AttributeError:
            first = None
        second = self.creative_file_extension
        if first or second:
            return [first, second]
        else:
            return None


class CDNServer(database.Base):
    __tablename__ = 'cdn_servers'

    id = Column(Integer, primary_key=True)
    fqdn = Column(String(254), unique=True, index=True)
    status = Column(Enum('up', 'maintenance', 'failed', name='cdn_server_status_type'), index=True)
    # 'banner_distr_status' column backref'ed from BannerDistStatus
    description = Column(UnicodeText)


class BannerDistStatus(database.Base):
    __tablename__ = 'banner_dist_status'

    id = Column(Integer, primary_key=True)
    counter_ref = Column(Integer, ForeignKey('counters.id'), index=True)
    counter = relationship("Counter", backref='banner_distr_status', cascade="all")
    cdn_server_ref = Column(Integer, ForeignKey('cdn_servers.id'), index=True)
    cdn_server = relationship("CDNServer", backref='banner_distr_status', cascade="all")
    time_stamp = Column(DateTime, index=True)
    banner_type = Column(Unicode(6))
    status = Column(Enum('ok', 'fail', 'disaster', name='banner_dist_status_type'), index=True)

    def __init__(self, counter=None, cdn_server=None, banner_type=None, status=None):
        self.counter = counter
        self.cdn_server = cdn_server
        self.time_stamp = datetime.datetime.utcnow()
        self.banner_type = banner_type
        self.status = status

    @validates('status')
    def update_timestamp(self, key, val):
        self.time_stamp = datetime.datetime.utcnow()
        return val

    @classmethod
    def update_status(cls, counter, cdn_server, banner_type, status):
        database.session.begin(subtransactions=True)
        try:
            inst = BannerDistStatus.query \
                .join(BannerDistStatus.counter,
                      BannerDistStatus.cdn_server) \
                .filter(Counter.id == counter.id,
                        CDNServer.id == cdn_server.id,
                        BannerDistStatus.banner_type == banner_type) \
                .one()
            inst.status = status
        except NoResultFound:
            record = BannerDistStatus(counter, cdn_server, banner_type, status)
            database.session.add(record)
        database.session.commit()


class AdLog(database.Base):
    __tablename__ = 'ad_logs'

    id = Column(Integer, primary_key=True)
    counter_ref = Column(Integer, ForeignKey('counters.id', ondelete='CASCADE'), index=True)
    counter = relationship("Counter", backref='logs', cascade="all")
    record_type = Column(Enum('clck',
                              'impr',
                              'impr_rej_cpc',
                              'clck_rej_geo',
                              'impr_rej_geo',
                              'clck_rej_browser',
                              'impr_rej_browser',
                              name='ad_log_record_type'), index=True)
    time_stamp = Column(DateTime, index=True)
    date_stamp = Column(Date, index=True)               # Auxiliary fields
    date_to_hour_stamp = Column(DateTime, index=True)   # for indexing purposes
    value = Column(Integer)

    def __init__(self, counter, record_type, time_stamp, value):
        self.counter = counter
        self.record_type = record_type
        if isinstance(time_stamp, datetime.datetime):
            self.time_stamp = time_stamp
            self.date_stamp = time_stamp.date()
            self.date_to_hour_stamp = time_stamp.replace(minute=0, second=0, microsecond=0)
        self.value = value


class CPC(database.Base):
    __tablename__ = 'CPCs'

    id = Column(Integer, primary_key=True)
    creative_ref = Column(Integer, ForeignKey('creatives.id', ondelete='CASCADE'), index=True)
    target_counter_ref = Column(Integer, ForeignKey('counters.id', ondelete='CASCADE'), index=True)
    contractor_ref = Column(Integer, ForeignKey('contractors.id', ondelete='CASCADE'), index=True)
    creative = relationship("Creative", backref='cpc', uselist=False, cascade="all")
    target_counter = relationship("Counter", cascade="all")
    contractor = relationship("Contractor", uselist=False, cascade="all")
    is_passthru = Column(Boolean)
    ctr_mean = Column(Float)
    ctr_deviation = Column(Float)
    clicks_overloaded = Column(Integer)
    external_campaign_id = Column(UnicodeText)
    description = Column(UnicodeText)


class GeoCountries(database.Base):
    __tablename__ = 'geo_countries'

    id = Column(Integer, primary_key=True)
    country_iso_id = Column(Unicode(2), unique=True, index=True)
    country_full_name = Column(Unicode(255), index=True)

    def __init__(self, country_iso_id, country_full_name):
        self.country_iso_id = country_iso_id
        self.country_full_name = country_full_name


class GeoCities(database.Base):
    __tablename__ = 'geo_cities'

    id = Column(Integer, primary_key=True)
    city_name = Column(Unicode(255), unique=True, index=True)

    def __init__(self, city_name):
        self.city_name = city_name
