# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

import logging
import socket
from logging.handlers import SysLogHandler, SMTPHandler
import configparser
import commonlib.exceptions


def get_logger(log_unit_name, *args, **settings):
    """
    :param log_unit_name: distinguished name of application which prepends each log record
    :param settings: is the same as for prepare_logger()
    """
    sys_logger = logging.getLogger(log_unit_name)
    prepare_logger(sys_logger, *args, **settings)
    return sys_logger


def prepare_logger(sys_logger, syslog_facility="LOG_USER",
                   crit_toemails=None, crit_mailhost='localhost', crit_fromemail='root',
                   crit_subject='CRITICAL logging notice',
                   log_syslog_address='localhost', log_syslog_proto='udp', log_syslog_port=514):
    """
    :param sys_logger: logger instance as result of logging.getLogger()
    :param syslog_facility: syslog facility
    :param crit_toemails: tuple of emails that is notified in case of CRITICAL event
    :param crit_mailhost: SMTP mail host for CRITICAL emails
    :param crit_fromemail: sender of CRITICAL emails
    :param crit_subject: email subject of CRITICAL emails
    :param log_syslog_address: Syslog server address, ether IP-address or FQDN
    :param log_syslog_proto: Syslog server ort type, either 'udp' or 'tcp'
    :param log_syslog_port: Syslog server port
    """

    # TODO switch to use YAML-based config file logging approach
    try:
        syslog_facility_arg = getattr(SysLogHandler, syslog_facility)
    except:
        raise Exception("Cannot determine the logging facility")
    if log_syslog_proto.lower() == 'udp':
        socktype = socket.SOCK_DGRAM
    elif log_syslog_proto.lower() == 'tcp':
        socktype = socket.SOCK_STREAM
    else:
        raise commonlib.exceptions.LoggerInitError
    syslog_handler = SysLogHandler(address=(log_syslog_address, log_syslog_port),
                                   facility=syslog_facility_arg, socktype=socktype)
    syslog_handler.setLevel(logging.INFO)
    syslog_formatter = logging.Formatter("%(name)s[%(process)s]: %(message)s")
    syslog_handler.setFormatter(syslog_formatter)
    sys_logger.addHandler(syslog_handler)
    if crit_toemails:
        # TODO make thread-safe throttling filter for email target
        crit_toemails_list = crit_toemails.split(',')
        smtp_handler = SMTPHandler(crit_mailhost, crit_fromemail, crit_toemails_list, crit_subject)
        smtp_handler.setLevel(logging.CRITICAL)
        smtp_formatter = logging.Formatter("CRITICAL event at %(asctime)%: %(name)s[%(process)s]: %(message)s")
        smtp_handler.setFormatter(smtp_formatter)
        sys_logger.addHandler(smtp_handler)


def logger_from_config(config):
    log_conf = configparser.config_section_obj(config, 'logging')
    # TODO switch to more compact form with getattr & kwargs or something like that
    return get_logger(log_conf.app_name, log_conf.facility, log_syslog_address=log_conf.syslog_address,
                      log_syslog_proto=log_conf.syslog_proto, log_syslog_port=int(log_conf.syslog_port),
                      crit_mailhost=log_conf.crit_mailhost,
                      crit_fromemail=log_conf.crit_fromemail,
                      crit_toemails=log_conf.crit_toemails,
                      crit_subject=log_conf.crit_subject)
