#!/bin/bash

echo "Checking for data"
wget -nc -nv -O /app/data/cphi.cache http://perfectlylegit.website/eunlg-data/cphi.cache
exec "$@"
