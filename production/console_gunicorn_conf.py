# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

bind = '0.0.0.0:8180'
workers = 2
worker_class = 'sync'   # Or may be 'tornado'
backlog = 32            # The maximum number of pending connections.
max_requests = 10000    # The maximum number of requests a worker will process before restarting.
user = 'olegvg'
syslog = True
syslog_addr = 'udp://localhost:5514'
syslog_prefix = 'console_gunicorn'
