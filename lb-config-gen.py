#!/usr/bin/env python3.5

nginx_pid_file = "/var/run/nginx.pid"
certificate_path = "/data/certs/live"
nginx_config_dir = "/etc/nginx"

base_config = """
user  nginx;
worker_processes  auto;

error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile        on;
    #tcp_nopush     on;

    keepalive_timeout  65;

    #gzip  on;

    #include /etc/nginx/conf.d/*.conf;

server {
    listen       80;
    server_name  localhost;
"""

refuse_service = """
    error_page   500 502 503 504 /50x.html;
    location = /50x.html {
        root   /usr/share/nginx/html;
    }
    location / {
        return 503;
    }
"""

base_config = base_config + refuse_service + "\n}\n\n"

service_https_vhost = """
UPSTREAM_GOES_HERE

server {
    listen 443 ssl http2;
    server_name SERVER_NAME_GOES_HERE;
    ssl_certificate CERTIFICATE_LOCATION_GOES_HERE/fullchain.pem;
    ssl_certificate_key CERTIFICATE_LOCATION_GOES_HERE/privkey.pem;

    # Performance + Privacy improvements
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate CERTIFICATE_LOCATION_GOES_HERE/fullchain.pem;
    resolver 8.8.8.8 208.67.222.222 valid=900s;
    resolver_timeout 3s;

    # https://mozilla.github.io/server-side-tls/ssl-config-generator/
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 5m;
    ssl_dhparam /etc/nginx/dhparams.pem;

    # https://www.owasp.org/index.php/List_of_useful_HTTP_headers
    add_header Strict-Transport-Security "max-age=10886400";
    add_header X-Content-Type-Options "nosniff";
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_pass http://origin-SERVER_NAME_GOES_HERE;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 900s;
    }

}
"""

service_http_vhost = """
server {
    listen 80;
    server_name SERVER_NAME_GOES_HERE;
    ACME_SECTION_GOES_HERE
    HANDLE_HTTP_GOES_HERE
}
"""

acme_section = """
    location /.well-known/acme-challenge {
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://origin-acme-service;
        proxy_http_version 1.1;
        proxy_read_timeout 900s;
    }
"""

#########

# Copyright 2016 Daniel Dent (https://www.danieldent.com/)

import time
import urllib.parse
import urllib.request
import json
import shutil
import re
import os.path
import signal

def get_current_services():
    headers = {
        'User-Agent': "rancher-nginx-active-lb/0.1",
        'Accept': 'application/json'
    }
    req = urllib.request.Request('http://rancher-metadata.rancher.internal/2015-12-19/containers', headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf8 '))

def upstream_config(hostname, ips):
    output = "upstream origin-" + hostname + " { \n"
    for ip in sorted(ips):
        output = output + "    server " + ip + ";\n"
    output = output + "\n}"
    return output

def vhost_config(hostname, ips, do_acme):
    config = service_http_vhost

    if do_acme:
        config = re.sub("ACME_SECTION_GOES_HERE", acme_section, config)
    else:
        config = re.sub("ACME_SECTION_GOES_HERE", "", config)


    if os.path.isdir(certificate_path + "/" + hostname):
        config = config + service_https_vhost
        config = re.sub("UPSTREAM_GOES_HERE", upstream_config(hostname, ips), config)
        config = re.sub("CERTIFICATE_LOCATION_GOES_HERE", certificate_path + "/" + hostname, config)
        config = re.sub("HANDLE_HTTP_GOES_HERE", "return 301 https://$server_name$request_uri;", config)
    else:
        config = re.sub("HANDLE_HTTP_GOES_HERE", refuse_service, config)

    config = re.sub("SERVER_NAME_GOES_HERE", hostname, config)

    return config

def get_nginx_config():
    acme_hosts = []
    published_hosts = {}

    for service in get_current_services():
        if service['state'] == 'running' and 'labels' in service and 'com.danieldent.rancher-nginx-active-lb.acme-host' in service['labels']:
            acme_hosts.append(service['primary_ip'])

        if service['state'] == 'running' and 'labels' in service and 'com.danieldent.rancher-nginx-active-lb.published-host' in service['labels']:
            for host in service['labels']['com.danieldent.rancher-nginx-active-lb.published-host'].split(","):
                if host in published_hosts:
                    published_hosts[host].append( service['primary_ip'] )
                else:
                    published_hosts[host] = [ service['primary_ip'] ]

    if len(acme_hosts) > 0:
        output = upstream_config("acme-service", acme_hosts)
        do_acme = 1
    else:
        do_acme = 0
        output = ""

    for host in sorted(published_hosts):
        output = output + vhost_config(host, published_hosts[host], do_acme)

    return output

if __name__ == '__main__':
    last_output = "EMPTYNESS"
    while True:
        full_output = base_config + get_nginx_config() + "}"
        if last_output != full_output:
            print("Generating configuration...")
            with open(nginx_config_dir + "/nginx.conf.temp", 'w') as config_file:
                print(full_output, file=config_file)
            shutil.move(nginx_config_dir + "/nginx.conf.temp", nginx_config_dir + "/nginx.conf")

            try:
                with open(nginx_pid_file, "r") as pid_file:
                    pid = int(pid_file.read())
                    os.kill(pid, signal.SIGHUP)
                    last_output = full_output
            except ProcessLookupError:
                print("Process in PID file not found, could not reload...")
                last_output = "EMPTYNESS"
            except FileNotFoundError:
                print("PID file not found, could not reload...")
                last_output = "EMPTYNESS"
            except ValueError:
                print("Could not parse PID file, could not reload...")
                last_output = "EMPTYNESS"
            except PermissionError:
                print("PID file permission error, could not reload...")
                last_output = "EMPTYNESS"

        time.sleep(30)
