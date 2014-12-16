# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from commonlib import configparser, logmaker, database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import redis
from celery import Celery
from celery.signals import worker_process_init

CONFIG_FILE = 'backend.conf'


logger = None

config = configparser.parse_config(CONFIG_FILE)

sqla_config = configparser.config_section_obj(config, 'sqlalchemy')
database.session = scoped_session(sessionmaker(autocommit=sqla_config.session_autocommit,
                                               autoflush=sqla_config.session_autoflush))
database.Base.query = database.session.query_property()
database.init_metadata()

celery = Celery('backend')
celery.config_from_object('backend_celery_conf')


@worker_process_init.connect
def engine_init(**kwargs):
    global logger
    logger = logmaker.logger_from_config(config)

    engine = create_engine(sqla_config.sqlserver_url)
    database.session.configure(bind=engine)

    redis_config = configparser.config_section_obj(config, 'redis')
    database.redisdb = redis.StrictRedis(host=redis_config.host, port=int(redis_config.port),
                                         db=redis_config.db, password=redis_config.password)