# rancher-nginx-active-lb

Dynamic automatic service discovery based load balancer using Nginx for Rancher environments.

First, launch this service. Then, launch a container with two special labels, e.g.:

```
example-service:
  image: nginx
  expose:
    - 80
  labels:
    com.danieldent.rancher-nginx-active-lb.published-host: example.com
    com.danieldent.rancher-lets-encrypt.hosts: example.com
```

An nginx configuration file is automatically generated based on which services are launched in the Rancher environment.
This service is designed for an all-SSL environment, and is a companion to
[rancher-lets-encrypt](https://gitlab.com/DanielDent/rancher-lets-encrypt).

The `com.danieldent.rancher-nginx-active-lb.published-host` label configures which hostnames will be routed to a
container by `rancher-nginx-active-lb`, while the `com.danieldent.rancher-lets-encrypt.hosts` label configures which
hostnames will have SSL certificates managed by rancher-lets-encrypt.

If load balancing is done by multiple hosts, this service assumes you are also making use of a system to synchronize the
docker volume on which certificates are stored. If a shared volume is not available, an example which uses Resilio Sync
to synchronize the certificate directory is available in the example folder.

Future versions may provide more flexibility in the type of nginx configuration which can be generated (e.g. support
for mounting containers on a path within a host). Pull requests are welcome.

# Future TODO

  * Investigate & configure Nginx's protection against repeated POST and other non-idempotent HTTP methods.
  * Refactor for greater readibility
  * Generalize configuration system

# License

The MIT License (MIT)

Copyright (c) 2016 [Daniel Dent](https://www.danieldent.com/)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
