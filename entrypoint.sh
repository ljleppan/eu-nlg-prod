#!/bin/bash

echo "Checking for data"
wget -nc -nv -O /app/data/cphi.cache http://perfectlylegit.website/eunlg-data/cphi.cache
wget -nc -nv -O /app/data/env.cache http://perfectlylegit.website/eunlg-data/env.cache
wget -nc -nv -O /app/data/health_cost.cache http://perfectlylegit.website/eunlg-data/health_cost.cache
wget -nc -nv -O /app/data/health_funding.cache http://perfectlylegit.website/eunlg-data/health_funding.cache
exec "$@"
