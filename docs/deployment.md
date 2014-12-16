Deployment onto single server
=============================


Assume that running user is 'olegvg'.

Under the `olegvg` user:

1. Create directory tree

        sudo mkdir /opt/production
        sudo setfacl -m u:olegvg:rwx /opt/production
        mkdir /opt/production/{apps,log,virtual_envs}
        mkdir /opt/production/log/me-advert
        mkdir /opt/production/virtual_envs/me-advert

2. Prepare login environment for git+ssh access to repository as mentioned [here](ssh_to_git.md)

3. Clone the last version

        git clone git@bitbucket.org:olegvg/me-advert.git /opt/production/apps/me-advert

4. Create virtual environment

        virtualenv /opt/production/virtual_envs/me-advert
        touch /opt/production/virtual_envs/me-advert.pip.env

5. Fill `me-advert.pip.env` with proper `pip --freeze` output

6. Install devel `.deb`-s which are needed to build `psycopg2` and `hiredis`

        source /opt/production/virtual_envs/me-advert/bin/activate
        pip install -r /opt/production/virtual_envs/me-advert.pip.env

7. Create symbolic links to supervisord configs

        sudo ln -s /opt/production/apps/me-advert/production/backend_supervisord.conf /etc/supervisor/conf.d/backend_supervisord.conf
        sudo ln -s /opt/production/apps/me-advert/production/rotabanner_supervisord.conf /etc/supervisor/conf.d/rotabanner_supervisord.conf
        sudo ln -s /opt/production/apps/me-advert/production/console_supervisord.conf /etc/supervisor/conf.d/console_supervisord.conf

7.-bis. Create symbolic links to supervisord configs for auxiliary services

        sudo ln -s /opt/production/apps/me-advert/production/dispenser_supervisord.conf /etc/supervisor/conf.d/dispenser_supervisord.conf

8. Create symbolic links to Nginx configs

        sudo ln -s /opt/production/apps/me-advert/production/rotabanner_nginx.conf /etc/nginx/sites-enabled/ads.media-nrg.ru
        sudo ln -s /opt/production/apps/me-advert/production/console_nginx.conf /etc/nginx/sites-enabled/service.media-nrg.ru

8.-bis. Create symbolic links to Nginx configs for auxiliary services

        sudo ln -s /opt/production/apps/me-advert/production/dispenser_nginx.conf /etc/nginx/sites-enabled/dispatch.edvent.ru

9. Create symbolic link to Syslog-ng config

        sudo ln -s /opt/production/apps/me-advert/production/me-advert_syslog.conf /etc/syslog-ng/conf.d/010me-advert.conf

10. Restart the services

        service syslog-ng restart
        supervisorctl
            >stop all
            >reread
            >start all
        service nginx restart
