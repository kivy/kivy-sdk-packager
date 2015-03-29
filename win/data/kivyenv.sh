# Script to initialize the complete dev environment
# for Kivy. Use that when you want to develop :)
#
# This will give you an access to :
# - Python binaries (python, easy_install)
# - Cython binaries (cython)
# - A correct pythonpath (Kivy)
# - Gstreamer binaries (gst-inspect, ...)
#
# Usage: source /path/to/kivyenv.sh
#

# Get root directory of portable installation
tmp=$(dirname $BASH_SOURCE)
export PY_VER=
export KIVY_PORTABLE_ROOT=$(cd $tmp; pwd)
export PYTHON_DIR=Python$PY_VER
export KIVY_DIR=kivy$PY_VER

if [ ! -d $KIVY_PORTABLE_ROOT ]; then
	echo "Usage: source /path/to/kivyenv.sh"
	exit 1
fi

# bootstrapping
echo bootstrapping Kivy @ $KIVY_PORTABLE_ROOT with Python $KIVY_PORTABLE_ROOT/$PYTHON_DIR

if [ "X$KIVY_PATHS_INITIALIZED" != "X1" ]; then

echo Setting Environment Variables:
echo #################################

export GST_REGISTRY=$KIVY_PORTABLE_ROOT/gstreamer/registry.bin
echo GST_REGISTRY is $GST_REGISTRY
echo ----------------------------------

export USE_SDL2=1
echo USE_SDL2 is $USE_SDL2
echo ----------------------------------

export GST_PLUGIN_PATH=$KIVY_PORTABLE_ROOT/gstreamer/lib/gstreamer-1.0
echo GST_PLUGIN_PATH is $GST_PLUGIN_PATH
echo ----------------------------------

export PATH=$KIVY_PORTABLE_ROOT:$KIVY_PORTABLE_ROOT/$PYTHON_DIR:$KIVY_PORTABLE_ROOT/$PYTHON_DIR/Scripts:$KIVY_PORTABLE_ROOT/gstreamer/bin:$KIVY_PORTABLE_ROOT/MinGW/bin:$KIVY_PORTABLE_ROOT/SDL2/bin:$PATH
echo PATH is $PATH
echo ----------------------------------

KIVY_PORTABLE_ROOT_WIN=$(python -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' $KIVY_PORTABLE_ROOT)
echo 'Convert to windows path:' $KIVY_PORTABLE_ROOT -\> $KIVY_PORTABLE_ROOT_WIN
echo ----------------------------------

export KIVY_SDL2_PATH=$KIVY_PORTABLE_ROOT_WIN\\SDL2\\lib\;$KIVY_PORTABLE_ROOT_WIN\\SDL2\\include\\SDL2\;$KIVY_PORTABLE_ROOT_WIN\\SDL2\\bin
echo KIVY_SDL2_PATH is $KIVY_SDL2_PATH
echo ----------------------------------

export PYTHONPATH=$KIVY_PORTABLE_ROOT_WIN\\kivy\;$PYTHONPATH
echo PYTHONPATH is $PYTHONPATH
export PKG_CONFIG_PATH=$KIVY_PORTABLE_ROOT/gstreamer/lib/pkgconfig\;$PKG_CONFIG_PATH

export KIVY_PATHS_INITIALIZED=1
echo ##################################

fi

echo done bootstraping kivy...have fun!
echo
