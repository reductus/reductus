import sys
########################################################################################
# Move this file to your webroot for deploy, and make an alias in apache site config:
#   AddHandler wsgi-script wsgi     Order allow,deny     Allow from all
#   WSGIScriptAlias /RPC2 /var/www/html/reflweb/reflweb_rpc.wsgi
########################################################################################

sys.path.append("path/to/reduction/reflweb_install")
from wsgi_app_init import application
