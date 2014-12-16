me-advert
=========

There is quite early version of Advertising Server which was used in Media Energy. At this point, all the code was written entirely by me. So this piece of software is entirely free under terms of GPL v3.
Following Python technologies and frameworks were used:
>- Flask / Jinja2
>- Tornado
>- Gunicorn
>- Celery / AMQP
>- Sqlalchemy
>- my own implementation of geoip lookup
>- supervisord
>- my own implementation of distribution mechanics of static objects over my own implemented CDN.

Other technologies:
>- PostgreSQL 9.1
>- Redis
>- JavaScript / jQuery
>- Twitter Bootstrap

There is an example how powerful Python (stock CPython) could be even in high load cases, even without Cython patches. Ad server proven sustains over 30000 requests per second with ordinary four-core CPU and 8 Gb of RAM.

### On installation
Deployment of frontend, backend and CDN explained [here](docs/deployment.md).
Some notes on Bitbucket integration and git hooks are [here](/docs/ssh_to_git.md).