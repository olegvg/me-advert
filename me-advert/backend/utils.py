# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'


from commonlib import database, configparser
from celery.task import Task


class SqlAlchemyTask(Task):
    """ I'm not sure whether previous decorator does the job. So there is an abstract Celery class which hooks
    'after_return' to ensure that SQLAlchemy session closed properly on task finish """

    abstract = True

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        database.session.remove()


def iterate_redis_set(s_name):
    while True:
        member = database.redisdb.spop(s_name)
        if member is not None:
            yield member
        else:
            break