#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Removes files and packages which are very likely not needed in a final app to help reduce the
final app size.

E.g. it removes the kivy examples, pip, headers, etc.

Usage: cleanup-app.sh <Path to bundle.app>

Requirements::

    A previously created bundle using create-osx-bundle.sh

For Example::

    ./cleanup-app.sh MyApp.app
"

if [ $# -lt 1 ]; then
    echo "$USAGE"
    exit 1
fi

pushd "$1"
APP_PATH="$(pwd)"
popd

VENV_PATH="$APP_PATH/Contents/Resources/venv"
rm -rf "$VENV_PATH"/share/kivy-examples
rm -rf "$VENV_PATH"/lib/python3.*/site-packages/kivy/{tools,tests}
rm -rf "$VENV_PATH"/bin/{cython*,cygdb,osxrelocator,pip*,pygmentize,easy_install*,rst*}
rm -rf "$VENV_PATH"/lib/python3.*/site-packages/{pip*,Cython*,setuptools*,osxrelocator*,cython*,wheel/test*}
rm -rf "$VENV_PATH"/lib/python3.*/site-packages/wheel/test


PYTHON_PATH=$(ls "$APP_PATH/Contents/Resources/python3")
rm -rf "$PYTHON_PATH/"lib/python3.*/{turtledemo,test,curses,unittest,ensurepip,idlelib,pydoc_data,setuptools*}
rm -rf "$PYTHON_PATH/"lib/python3.*/site-packages/{easy_install*,pip*,virtualenv,setuptools*}
rm -rf "$PYTHON_PATH/"lib/python3.*/site-packages/wheel/test
rm -rf "$PYTHON_PATH"/lib/python3.*/sqlite3
rm -rf "$PYTHON_PATH"/lib/python3.*/tkinter
rm -rf "$PYTHON_PATH/"bin/{pygmentize,2to*,pip*,*-config,easy_install*,idle*,pydoc*,rst*,pip*}
rm -rf "$PYTHON_PATH/"lib/{lib*,pkgconfig}
rm -rf "$PYTHON_PATH/"include
rm -rf "$PYTHON_PATH"/lib/pkgconfig
rm -rf "$PYTHON_PATH"/lib/{itcl*,tcl*,tdbc*,tk*,tK*,libtk*,libtcl*}
