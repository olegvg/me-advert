# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

import subprocess

if __name__ == "__main__":
    subprocess.call(['celery', 'worker', '-B', '-E',
                     '--config=backend_celery_conf',
                     '--schedule=../tmp/celerybeat-schedule',
                     '--autoreload'])