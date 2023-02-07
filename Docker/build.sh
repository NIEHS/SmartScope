#! /bin/bash

echo -n "Version name: "
read VERSION

echo -n "Branch name: "
read BRANCH

docker build \
    --label org.opencontainers.image.documentation=https://docs.smartscope.org/docs/$BRANCH/index.html \
    --label org.opencontainers.image.version=$VERSION \
    -t smartscope:$VERSION -f Docker/Dockerfile-smartscope .