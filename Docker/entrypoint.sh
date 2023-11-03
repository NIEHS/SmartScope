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
  echo "Using SSL nginx template, Alternate login = $ALTERNATE_LOGIN"
  if $ALTERNATE_LOGIN; then
    echo "Using alternate login template"
    nginx_conf=/opt/smartscope/config/docker/templates_SSL/alternate_login.conf
  else
    nginx_conf=/opt/smartscope/config/docker/templates_SSL/default.conf
  fi
else
  echo "Using noSSL nginx template"
  if [[ "${ALTERNATE_LOGIN,,}" == "true" ]]; then
    echo "Using alternate login template"
    nginx_conf=/opt/smartscope/config/docker/templates_noSSL/alternate_login.conf
  else
    nginx_conf=/opt/smartscope/config/docker/templates_noSSL/default.conf
  fi
fi
cp $nginx_conf /opt/shared/default.conf


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
secret_key_file="/opt/auth/secret_key.txt"

if [ -e "$secret_key_file" ]; then
    echo "Secret key file exists...reading"
else
    secret_key=;
    echo "Secret key file does not exist. Creating and setting permissions..."
    echo $($RANDOM | md5sum | head -c 25) > "$secret_key_file"
    chmod 600 "$secret_key_file"
    echo "Secret key file created and permissions set."
fi
export SECRET_KEY=$(cat "$secret_key_file");

env | sort

#Run migrations if any
if $AUTO_MIGRATION; then
  echo "Running migrations"
  manage.py migrate
fi

#Execute cmd statements
exec "$@"