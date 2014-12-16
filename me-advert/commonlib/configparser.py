# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

import ConfigParser
from exceptions import ConfigParserError


def parse_config(file):
    cfg = ConfigParser.RawConfigParser()
    cfg.read(file)
    return cfg


def config_section_obj(cfg, section_name):
    class ConfigObj(object):
        if cfg is None:
            raise ConfigParserError("invalid 'cfg' in config_section_obj()")
        _config_dict = dict(cfg.items(section_name))

        def __getattr__(self, item):
            try:
                return self._config_dict[item]
            except KeyError:
                raise ConfigParserError("invalid 'cfg' in config_section_obj()")

        def __setattr__(self, key, value):
            raise ConfigParserError("try to write  parameter '{}' with value '{}'".format(
                key, value))

    return ConfigObj()