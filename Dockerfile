FROM odoo:latest

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements.txt

USER odoo


FROM odoo:19
COPY ./comics_collections /mnt/extra-addons/
