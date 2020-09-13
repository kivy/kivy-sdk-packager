#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Fixes the paths of scripts and removes compiled pyc/pyo files. This is required so that
the bundle created with create-osx-bundle.sh could be moved to a different path or made into a
dmg.

The should be run every time after new packages are installed into the venv before
a dmg is created or before the bundle is moved to a different path.

Usage: relocate.sh <Path to bundle.app>

Requirements::

    A previously created bundle using create-osx-bundle.sh

For Example::

    ./relocate.sh MyApp.app
"

if [ $# -lt 1 ]; then
    echo "$USAGE"
    exit 1
fi

pushd "$1"
APP_PATH="$(pwd)"
popd

echo "Remove path specific pyc files"
pushd "$APP_PATH/Contents/Frameworks/Python.framework"
find . -name "*.pyc" -print0 | xargs -0 rm
find . -name "*.pyo" -print0 | xargs -0 rm

echo "Making scripts relative"
pushd "$APP_PATH/Contents/Resources/venv/bin"

(export LANG=C LC_ALL=C; find . -type f -name '*' -print0 | \
    xargs -0  sed -i '.bak' "s~#\\!$APP_PATH/Contents/Resources/venv/bin/python~#\\!/usr/bin/env python~")
rm -f ./*.bak

popd
popd


echo "Done"
