# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from commonlib import database as db
from commonlib.model import Counter, Creative, BannerDistStatus, CDNServer
import backend
from backend import celery
from backend.utils import SqlAlchemyTask
from sqlalchemy.orm import joinedload
import requests


@celery.task(base=SqlAlchemyTask)
def init_redis_with_counter(counter_id):

    distribute_banners_to_cdn.delay(counter_id)

    counter = Counter.query \
        .options(joinedload(Counter.creative,
                            Creative.campaign),
                 joinedload(Counter.creative,
                            Creative.creative_format)) \
        .filter(Counter.uniq_id == counter_id) \
        .one()
    if counter is None:
        backend.logger.critical(u"it has just been asked for counter '{}' which is absent".format(counter_id))
        return None

    campaign_state = counter.creative.campaign.state
    if campaign_state != 'active':
        backend.logger.critical(u"it has just been asked for counter '{}' which "
                                u"connects with {} company '{}'".format(counter_id, campaign_state,
                                                                        counter.creative.campaign.name))
        if campaign_state == 'archived':
            return None

    counter_key = 'counter-{}'.format(counter_id)
    click_target_url = counter.creative.click_target_url
    impression_target_url = counter.creative.impression_target_url
    impression_target_url = impression_target_url if impression_target_url else u''
    mu_ctr = counter.mu_ctr if counter.mu_ctr else ''
    sigma_ctr = counter.sigma_ctr if counter.sigma_ctr else ''

    try:
        geo_cities = u'|'.join(counter.creative.geo_cities)
    except TypeError:
        geo_cities = u''
    try:
        geo_countries = u'|'.join(counter.creative.geo_countries)
    except TypeError:
        geo_countries = u''

    if counter.creative.creative_format.are_dimensions_int:
        dimensions = counter.creative.creative_format.dimension_x + u'x' + counter.creative.creative_format.dimension_y
    else:
        dimensions = u''

    banner_exts = counter.banner_types
    if banner_exts:
        extensions = u','.join(map(lambda x: x if x else u'', banner_exts))
    else:
        extensions = u''

    with db.redisdb.pipeline() as pipe:
        pipe.set(counter_key, campaign_state)
        pipe.set('counter-{}-clck-target-url'.format(counter_id), click_target_url)
        pipe.set('counter-{}-impr-target-url'.format(counter_id), impression_target_url)
        pipe.set('counter-{}-cpc-mu-ctr'.format(counter_id), mu_ctr)
        pipe.set('counter-{}-cpc-sigma-ctr'.format(counter_id), sigma_ctr)
        pipe.set('counter-{}-banner-dimensions'.format(counter_id), dimensions)
        pipe.set('counter-{}-banner-exts'.format(counter_id), extensions)
        pipe.set('creative-geo-cities-{}'.format(counter_id), geo_cities)
        pipe.set('creative-geo-countries-{}'.format(counter_id), geo_countries)
        pipe.execute()
    return counter_key


@celery.task(base=SqlAlchemyTask)
def distribute_banners_to_cdn(counter_id):
    counter = Counter.query \
        .filter(Counter.uniq_id == counter_id) \
        .one()

    servers = CDNServer.query \
        .filter(CDNServer.status == 'up') \
        .all()

    banners = ((counter.creative_filename_swf, counter.creative_file_swf), (
        counter.creative_filename_gif, counter.creative_file_gif))

    for filename, content in banners:
        if content is None or filename is None:
            continue
        extension = filename.rsplit('.', 1)[-1]
        for server in servers:
            try:
                resp = requests.put('http://' + server.fqdn + '/' + counter.uniq_id + '.' + extension,
                                    data=content,
                                    headers={'content-type': 'application/octet-stream'})
                status = 'ok' if 200 <= resp.status_code <= 299 else 'fail'
            except requests.ConnectionError:
                status = 'disaster'
            BannerDistStatus.update_status(counter, server, extension, status)
