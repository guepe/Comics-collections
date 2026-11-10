#!/bin/bash
# usage: shell.sh script.py  (script path relative to /work)
~/.docker/bin/docker exec -i appstore-odoo odoo shell --db_host postgres-Odoo -r odoo -w odoo -d appstore_demo --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons --no-http --log-level=warn < "$1"
