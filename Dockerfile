FROM odoo:19

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements.txt

USER odoo

# Les modules (comics_collections, comic_datasource, comic_shop, …) sont montés
# en volume dans /mnt/extra-addons/<module> par docker-compose — pas de COPY ici.
