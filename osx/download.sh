#!/usr/bin/env zsh
set -x  # verbose
set -e  # exit on error

USAGE="Download a URL using curl only if the file does not already exist locally
Usage: download.sh <url>
Requirements::
    curl pre-installed in the PATH
For Example::
    ./download.sh http://www.openssl.org/source/openssl-1.1.1l.tar.gz
"

if [ $# -lt 1 ]; then
    echo "$USAGE"
    exit 1
fi

URL="$1"
FILE="$URL:t"

if [ ! -f "$FILE" ]; then
    curl -L -O "$URL"
fi
ls -l "$FILE"
echo "Done download.sh $URL"