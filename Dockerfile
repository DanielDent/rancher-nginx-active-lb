FROM danieldent/ubuntu-xenial-base
MAINTAINER Daniel Dent (https://www.danieldent.com/)
RUN /usr/local/bin/add-repo-nginx.sh \
    && DEBIAN_FRONTEND=noninteractive apt-get update -q \
    && /usr/local/bin/install-nginx.sh 1.10.2-1~xenial \
    && /usr/local/bin/install-nginx-log-symlinks.sh \
    && mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.default \
    && /usr/local/bin/install-s6-overlay.sh \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y python3-urllib3
COPY dhparams.pem /etc/nginx
COPY default-server-cert /etc/nginx/default-server-cert
COPY errorpages/* /usr/share/nginx/html/
COPY services.d/nginx /etc/services.d/nginx
COPY services.d/lb-config-gen /etc/services.d/lb-config-gen
COPY services.d/autoreload /etc/services.d/autoreload
COPY lb-config-gen.py /
ENTRYPOINT ["/init"]
