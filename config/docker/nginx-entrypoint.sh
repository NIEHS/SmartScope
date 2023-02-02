#! /bin/bash

cp /opt/shared/default.conf /etc/nginx/conf.d/default.conf 
nginx -g "daemon off;"