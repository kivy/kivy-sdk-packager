#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Usage::

    relocate.sh <app_root>

For Example::

    sh ./relocate.sh Kivy.app
"

if [ $# -lt 1 ]; then
    echo "$USAGE"
    exit 1
fi

pushd "$1"
APP_PATH="$(pwd)"
popd

echo "Remove path specific pyc files"
pushd "$APP_PATH/Contents/Resources/venv"
grep -irl --include=\*.pyc "$APP_PATH/Contents/Resources/venv" . | xargs rm

echo "Making scripts relative"
(export LANG=C LC_ALL=C; find . -type f -name '*' -print0 | xargs -0  sed -i '.bak' "s~$APP_PATH/Contents/Resources/venv/bin/python~/usr/bin/env python~")
sed -E -i '.bak' 's#^VIRTUAL_ENV=.*#VIRTUAL_ENV=$(cd $(dirname "$BASH_SOURCE"); dirname `pwd`)#' bin/activate
find . -type f -name "*.bak" -print0 | xargs -0 rm
popd

echo "Done"
