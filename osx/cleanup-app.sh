#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Removes files and packages which are very likely not needed in a final app to help reduce the
final app size.

E.g. it removes the kivy examples, pip, headers, etc.

Usage: cleanup-app.sh <Path to bundle.app> [options]

    -g --remove-gstreamer     <Remove gstreamer, default:0>        \
Whether gstreamer should be removed from the package. One of 0 or 1.

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

shift

REMOVE_GSTREAMER="0"
while [[ "$#" -gt 0 ]]; do
    # empty arg?
    if [ -z "$2" ]; then
        echo "$USAGE"
        exit 1
    fi

    case $1 in
        -g|--remove-gstreamer) REMOVE_GSTREAMER="$2";;
        *) echo "Unknown parameter passed: $1"; echo "$USAGE"; exit 1 ;;
    esac
    shift; shift
done

if [ "$REMOVE_GSTREAMER" != "0" ]; then
    rm -rf "$APP_PATH/Contents/Frameworks/GStreamer.framework"
fi

VENV_PATH="$APP_PATH/Contents/Resources/venv"
rm -rf "$VENV_PATH"/share/kivy-examples
rm -rf "$VENV_PATH"/lib/python3.*/site-packages/kivy/{tools,tests}
rm -rf "$VENV_PATH"/bin/{cython*,cygdb,osxrelocator,pip*,pygmentize,easy_install*,rst*}
rm -rf "$VENV_PATH"/lib/python3.*/site-packages/{pip*,Cython*,setuptools*,osxrelocator*,cython*,wheel/test*}
rm -rf "$VENV_PATH"/lib/python3.*/site-packages/wheel/test


PYTHON_PATH=$(ls "$APP_PATH/Contents/Frameworks/Python.framework/Versions"/3*)
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
