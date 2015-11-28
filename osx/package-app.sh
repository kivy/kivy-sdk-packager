#!/bin/bash

set -x  # verbose
if [ "X$1" == "X" ]; then
	echo "Usage: $(basename $0) path/to/your/app"
	exit 1
fi

set -e  # exit on error

SCRIPT_PATH="${BASH_SOURCE[0]}";
if([ -h "${SCRIPT_PATH}" ]) then
  while([ -h "${SCRIPT_PATH}" ]) do SCRIPT_PATH=`readlink "${SCRIPT_PATH}"`; done
fi
SCRIPT_PATH=$(python -c "import os; print os.path.realpath(os.path.dirname('${SCRIPT_PATH}'))")
KIVY_APP="${SCRIPT_PATH}/Kivy.app"

if [ ! -f "${KIVY_APP}" ]; then
	echo "No Kivy.app generated, use create-osx-bundle.sh first."
fi

echo "-- Get the name of your app"
APPNAME="$(basename $1)"
APPPATH="${SCRIPT_PATH}/${APPNAME}.app"
echo "Hello, ${APPNAME}"

echo "-- Duplicate the Kivy.app to ${APPNAME}.app"
cp -a "${SCRIPT_PATH}/Kivy.app" "${APPPATH}"

echo "-- Copy your application"
cp -a "$1" "${APPPATH}/Contents/Resources/yourapp"

echo "-- Optimize all python files"
source "${APPPATH}/Contents/Resources/venv/bin/activate"
python -OO -m compileall "${APPPATH}"

echo "-- Remove all py/pyc"
find -E "${APPPATH}" -regex ".*pyc?$" -exec rm {} \;
