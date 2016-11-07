FROM klaemo/couchdb:2.0.0
COPY ./docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
