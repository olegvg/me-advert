# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import expression
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import DateTime
from sqlalchemy.sql import compiler
from psycopg2.extensions import adapt as sqlescape

Base = declarative_base()
session = None

redisdb = None


def init_metadata():
    import model            # initialise model by import


def create_db(engine):
    if engine is not None:
        Base.metadata.create_all(bind=engine)


def drop_db(engine):
    if engine is not None:
        Base.metadata.drop_all(bind=engine)


class in_time(expression.FunctionElement):
    type = DateTime()
    name = 'in_time'


@compiles(in_time, 'postgresql')
def pg_in_time(element, compiler, **kw):
    field, interval = list(element.clauses)
    return "{} >= TIMEZONE('utc', CURRENT_TIMESTAMP) - interval {}" \
        .format(compiler.process(field), compiler.process(interval))


def compile_query(query):
    dialect = query.session.bind.dialect
    statement = query.statement
    comp = compiler.SQLCompiler(dialect, statement)
    comp.compile()
    enc = dialect.encoding
    params = {}
    for k, v in comp.params.iteritems():
        if isinstance(v, unicode):
            v = v.encode(enc)
        params[k] = sqlescape(v)
    return (comp.string.encode(enc) % params).decode(enc)