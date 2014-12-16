# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from celery.schedules import crontab

CELERY_TIMEZONE = 'Europe/Moscow'

CELERYD_CONCURRENCY = 4

BROKER_URL = 'redis://10.49.7.4:6379/7'
CELERY_RESULT_BACKEND = 'redis://10.49.7.4:6379/7'
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
CELERY_REDIS_MAX_CONNECTIONS = 25
CELERY_IMPORTS = ("backend.tasks.servant", "backend.tasks.periodic", "backend.tasks.surfingbird")

CELERYBEAT_SCHEDULE = {
    'store_events-every-2-minutes': {
        'task': 'backend.tasks.periodic.store_events',
        'schedule': crontab(minute='*/2')
    },
    'recalculate_ctrs-every-5-minutes': {
        'task': 'backend.tasks.periodic.recalculate_ctrs',
        'schedule': crontab(minute='*/5')
    },
    'update_per_campaign_sites_report-every-night': {
        'task': 'backend.tasks.periodic.update_per_campaign_sites_report',
        'schedule': crontab(minute=30, hour=0)
    },
    # 'check_campaign_period-every-midnight': {
    #     'task': 'backend.tasks.periodic.check_campaign_period',
    #     'schedule': crontab(minute=0, hour=0)
    # },
    # 'buy_surfingbird_clicks-every-5-minutes': {
    #     'task': 'backend.tasks.surfingbird.buy_surfingbird_clicks',
    #     'schedule': crontab(minute='*/5')
    # },
    # 'clear_surfingbird_campaigns-5-minutes-before-midnight': {
    #     'task': 'backend.tasks.surfingbird.clear_surfingbird_campaigns',
    #     'schedule': crontab(minute=57, hour=23)
    # }
}
