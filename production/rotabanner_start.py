# -*- coding: utf-8 -*-

__author__ = 'ogaidukov'

# This startup script runs as Python script, with current directory is a directory of this script and
# params (ex.): ./rotabanner.conf --listen 8080
#
# VIRTUALENV_PATH environment variable has to point to virtualenv directory


import os

virtualenv_path = os.environ['VIRTUALENV_PATH']
activate_this_script = os.path.join(virtualenv_path, 'bin', 'activate_this.py')
execfile(activate_this_script, dict(__file__=activate_this_script))

from rotabanner.application import run_application

if __name__ == '__main__':
    run_application()
