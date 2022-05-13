#!/bin/bash

cd $(dirname "$(readlink -f "$0")")
pwd
echo 'Setting smartscope environment'
set -a
. ../conf.env
set +a

source $CONDA_INSTALL/activate smartscope

echo "Dumping $DB_NAME"
mysqldump --user=$MYSQL_USERNAME --password=$MYSQL_ROOT_PASSWORD $DB_NAME > /home/autoprocess/sync.sql
echo "Transfering file to remote host"
scp -i /home/autoprocess/smartscope-virginia.pem /home/autoprocess/sync.sql ec2-user@50.16.209.66:~/
echo "Overwriting datase in remote host "
ssh -i /home/autoprocess/smartscope-virginia.pem ec2-user@50.16.209.66 "mysql --user $MYSQL_USERNAME -p$MYSQL_ROOT_PASSWORD autoscreenViewer < sync.sql"