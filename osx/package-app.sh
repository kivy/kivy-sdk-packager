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
SCRIPT_PATH=$(python -c "import os;print(os.path.realpath(os.path.dirname('${SCRIPT_PATH}')))")
KIVY_APP="${SCRIPT_PATH}/Kivy.app"

if [ ! -f "${KIVY_APP}" ]; then
	echo "No Kivy.app generated, use create-osx-bundle.sh first."
fi

echo "-- Get the name of your app"
APPNAME="$(basename $1)"
APPPATH="${SCRIPT_PATH}/${APPNAME}.app"
echo "Hello, ${APPNAME}"

echo "-- Duplicate the Kivy.app to ${APPNAME}.app"
cp -a ${SCRIPT_PATH}/Kivy.app ${APPPATH}

echo "-- Copy your application"
cp -a $1 ${APPPATH}/Contents/Resources/myapp

echo "-- Optimize all python files"
source ${APPPATH}/Contents/Resources/venv/bin/activate

#check python Versions
if python -c 'import sys; sys.exit(1 if sys.hexversion<0x03000000 else 0)'
then
	${APPPATH}/Contents/Resources/script -OO -m compileall -b ${APPPATH}/Contents/Resources/
	mv ${APPPATH}/Contents/Resources/myapp ${APPPATH}/Contents/Resources/yourapp
	echo "Remove all __pycache__"
  find -E ${APPPATH}/Contents/Resources -regex "(.*)\.py" | xargs rm
	find -E ${APPPATH}/Contents/ -name "__pycache__"| xargs rm -rf
else
	${APPPATH}/Contents/Resources/script -OO -m compileall ${APPPATH}/Contents/Resources/
	mv ${APPPATH}/Contents/Resources/myapp ${APPPATH}/Contents/Resources/yourapp
	echo "-- Remove all py/pyc"
  find -E ${APPPATH} -regex ".*pyc?$" | xargs rm -r
fi


# check for icon
PYPATH="$APPPATH/Contents/Frameworks/pythoh"
rm -rf "$PYPATH/3.5.0/lib/python3.5/sqlite3"
rm -rf "$APPPATH/3.5.0/lib/python3.5/tkinter"
rm -rf "$PYPATH/3.5.0/bin/{pygmentize,2to*,pip*,*-config,easy_install*,idle*,pydoc*,python3.5m*,rst*}"
rm -rf "$PYPATH/3.5.0/lib/{lib*,pkgconfig,turtledemo,unittest}"
rm -rf "$PYPATH/3.5.0/lib/pkgconfig"
rm -rf "$PYPATH/3.5.0/lib/python3.5/{turtledemo,unittest,curses,distutils,ensurepip,idlelib,pydoc_data,setuptools*}"
rm -rf "$APPPATH/Contents/Resources/kivy/doc"
rm -rf "$APPPATH/Contents/Resources/kivy/kivy/tools"
rm -rf "$APPPATH/Contents/Resources/kivy/examples"
rm -rf "$APPPATH/Contents/Resources/kivy/build"
rm -rf "$APPPATH/Contents/Resources/venv/lib/python2.7/site-packages/distutils"
rm -rf "$APPPATH/Contents/Resources/venv/lib/python2.7/site-packages/pip"
rm -rf "$APPPATH/Contents/Resources/venv/lib/python2.7/site-packages/pygments/"
rm -rf "$APPPATH/Contents/Resources/venv/lib/python2.7/site-packages/Cython/"
