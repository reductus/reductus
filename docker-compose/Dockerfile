FROM httpd:alpine
RUN apk add --no-cache git apache2 bash apache2-proxy
ENV apachedir /usr/local/apache2
COPY reflweb/static $apachedir/htdocs/reflweb
RUN sed -i '/mod_proxy\.so/s/^#//g' $apachedir/conf/httpd.conf
RUN sed -i '/mod_proxy_http\.so/s/^#//g' $apachedir/conf/httpd.conf
RUN sed -i '/Include conf\/extra\/httpd-vhosts\.conf/s/^#//g' $apachedir/conf/httpd.conf
COPY docker-compose/httpd-vhosts.conf $apachedir/conf/extra/httpd-vhosts.conf
RUN echo '{}' > $apachedir/htdocs/reflweb/rpc_config.json
EXPOSE 80
