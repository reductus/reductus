#!/bin/bash

REDUCTUS_HOME=$HOME/reductus
REDUCTUS_VENV=$HOME/reductus-venv
REDUCTUS_WORK_DIR=$HOME/reductus-work
PROVISION_DIR=$REDUCTUS_HOME/provisioning/ubuntu22

sudo apt update
sudo apt install -y apache2 apache2-dev libapache2-mod-proxy-uwsgi python3-venv

# apache setup
sudo a2enmod headers proxy_uwsgi
sudo systemctl restart apache2

sudo mkdir /var/www/html/reductus
# sudo cp -r $REDUCTUS_HOME/reductus/web_gui/static/* /var/www/html/reductus
sudo chown -R $USER:$USER /var/www/html/reductus
sudo chmod -R a+r /var/www/html/reductus
sudo find /var/www/html -type d -exec chmod 755 {} \;
# only need this if ansible has set this to permissions 750:
#sudo chmod a+x /var/spool/cron;

# get the application code...
git clone https://github.com/reductus/reductus $REDUCTUS_HOME
cp $PROVISION_DIR/post-merge $REDUCTUS_HOME/.git/hooks/post-merge
chmod +x $REDUCTUS_HOME/.git/hooks/post-merge
$REDUCTUS_HOME/.git/hooks/post-merge

# make a virtualenv
python3 -m venv $REDUCTUS_VENV

$REDUCTUS_VENV/bin/pip install -e $REDUCTUS_HOME[server]
$REDUCTUS_VENV/bin/pip install h5py wheel diskcache uwsgi pylru lz4

mkdir -p $REDUCTUS_WORK_DIR
cp $PROVISION_DIR/uwsgi.ini $REDUCTUS_WORK_DIR/uwsgi.ini

sudo cp $PROVISION_DIR/reductus.service /etc/systemd/system/reductus.service
sudo systemctl enable reductus
sudo systemctl start reductus

# copy the config.py from server...
cp $PROVISION_DIR/config.py $REDUCTUS_HOME/configurations/config.py

# set up vhosts file...
sudo cp $PROVISION_DIR/reductus.conf /etc/apache2/sites-available/reductus.conf
# copy SSL keys (MANUAL FOR NOW!)
# sudo mkdir /etc/apache2/ssl
# sudo chmod 700 /etc/apache2/ssl
# manually copy /etc/apache2/ssl/*.crt and *.key to the new host, and
# sudo chmod 600 /etc/apache2/ssl/*
sudo a2dissite 000-default
sudo a2ensite reductus

# start the website
sudo service apache2 reload

# use iptables directly if ansible script causes ufw to not work
# sudo iptables -A INPUT -p tcp --dport 80 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
# sudo iptables -A INPUT -p tcp --dport 443 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
# sudo netfilter-persistent save

# use ufw if available/working
# sudo ufw allow ssh
# sudo ufw allow http
# sudo systemctl enable ufw
# sudo ufw reload

# firewall-cmd --add-service=ssh --permanent
firewall-cmd --add-service=http --permanent
firewall-cmd --reload

# set up apache2 to keep log files longer
sudo sed -i -e 's/rotate [0-9]\+/rotate 31/g' /etc/logrotate.d/apache2

