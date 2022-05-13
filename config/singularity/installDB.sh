#!/bin/bash
echo "Initial Database setup"
mysql_install_db --defaults-file=/opt/smartscope/config/singularity/db.cnf;
mysqld_safe --defaults-file=/opt/smartscope/config/singularity/db.cnf &
sleep 5
mysql -e 'CREATE DATABASE smartscope'
mysql smartscope < /opt/smartscope/config/baseDB.sql
mysqladmin --wait-for-all-slaves shutdown
echo "Done. Now creating a secret key"
echo $RANDOM | md5sum | head -c 25 > /mnt/mariadb/secretkey.txt
echo $RANDOM | md5sum | head -c 25 >> /mnt/mariadb/secretkey.txt
echo "Saved in /mnt/mariadb/secretkey.txt"

