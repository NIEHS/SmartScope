#! /bin/bash

#Copy shared data to mount
cp /opt/smartscope/config/docker/nginx-entrypoint.sh /opt/shared/
cp -r /opt/smartscope/static /opt/shared/

version=$(cat /opt/config/version)
echo "Config version is \"$version\" and current version is \"$VERSION\""
if [ "$version" != "$VERSION" ]; then
  echo 'Updating config'
  echo $VERSION > /opt/config/version
  mkdir -p /opt/config/plugins /opt/config/protocols
  cp /opt/smartscope/config/smartscope/* /opt/config/
fi

if $USE_SSL; then
  echo "Using SSL nginx template"
  cp /opt/smartscope/config/docker/templates_SSL/default.conf /opt/shared/
else
  echo "Using noSSL nginx template"
  cp /opt/smartscope/config/docker/templates_noSSL/default.conf /opt/shared/
fi


#Make sure that the database server is running first.
until mysqladmin ping --user=$MYSQL_USER --password=$MYSQL_PASSWORD --host=$MYSQL_HOST > /dev/null;
do
  echo "Database server is not up. Will retryn in 2 seconds"
  sleep 2
done
echo "Database server is running."

#Check that the database already exists
result=$(mysql -s -N --user=$MYSQL_USER --password=$MYSQL_PASSWORD --host=$MYSQL_HOST $DB_NAME -e "SHOW TABLES");
if [ -z "$result" ];
then
  echo "DATABASE DOES NOT EXIST, INITIATING DB."
  mysql --user=$MYSQL_USER --password=$MYSQL_PASSWORD --host=$MYSQL_HOST $DB_NAME < config/docker/initialdb.sql;
else
  echo "DATABASE EXISTS"
fi

# Create a random secret key for hashing requests
export SECRET_KEY=$($RANDOM | md5sum | head -c 25);

env | sort

#Run migrations if any
if $AUTO_MIGRATION; then
  echo "Running migrations"
  manage.py migrate
fi

#Execute cmd statements
exec "$@"