#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Creates a Kivy bundle that can be used to build your app into a dmg. See documentation.

Usage::

    create-osx-bundle.sh <Kivy version or path> <Python version> <App name> <App version> <Author> <org> <icon> <app_main_script>

Requirements::

    The SDL2, SDL2_image, SDL2_ttf, and SDL2_mixer frameworks needs to be installed.
    If gstreamer is enabled (the default), gstreamer-1.0 also need to be installed.
    To disable gstreamer, export USE_GSTREAMER=0 and it won't be packaged.

    Platypus also needs to be installed.

For Example, to build Kivy we use::

    ./create-osx-bundle.sh 1.11.1 3.7.4 Kivy 1.11.1 \"Kivy Developers\" org.kivy.osxlauncher data/icon.icns data/script
"

if [ $# -lt 8 ]; then
    echo "$USAGE"
    exit 1
fi

# get kivy path or url
KIVY_PATH="$1"
if [ -d "$KIVY_PATH" ]; then
    # get full path
    pushd "$KIVY_PATH"
    KIVY_PATH="$(pwd)"
    popd
else
    KIVY_PATH="https://github.com/kivy/kivy/archive/$KIVY_PATH.zip"
fi

echo "Using Kivy $KIVY_PATH"

PYVER="$2"
echo "Using Python version $PYVER"

APP_NAME="$3"
APP_VERSION="$4"
AUTHOR="$5"
APP_ORG="$6"
echo "Build $APP_NAME version $APP_VERSION org $APP_ORG by $AUTHOR"

ICON_PATH="$6"
APP_SCRIPT="$7"
echo "App will launch with $APP_SCRIPT using icon $ICON_PATH"

PLATYPUS=/usr/local/bin/platypus
if [ ! -f "$PLATYPUS" ]; then
    echo "Could not find platypus at $PLATYPUS"
    exit 1
fi

SCRIPT_PATH="${BASH_SOURCE[0]}"
PYTHON=python3
USE_GSTREAMER=${USE_GSTREAMER:-1}

# follow any symbolic links
if [ -h "${SCRIPT_PATH}" ]; then
  while [ -h "${SCRIPT_PATH}" ]; do
      SCRIPT_PATH=$(readlink "${SCRIPT_PATH}")
  done
fi

SCRIPT_PATH=$($PYTHON -c "import os; print(os.path.realpath(os.path.dirname('$SCRIPT_PATH')))")
OSXRELOCATOR="osxrelocator"


echo "-- Create initial $APP_NAME.app package"
$PLATYPUS -DBR -x -y \
    -i "$ICON_PATH" \
    -a "$APP_NAME" \
    -o "None" \
    -p "/bin/bash" \
    -V "$APP_VERSION" \
    -I "$APP_ORG" \
    -X "*" \
    "$APP_SCRIPT" \
    "$SCRIPT_PATH/$APP_NAME.app"


echo "--- Frameworks"

echo "-- Create Frameworks directory"
mkdir -p "$APP_NAME.app/Contents/Frameworks"

echo "Install Python"
if [ ! -f ~/.pyenv/bin/pyenv ]; then
  curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
  ~/.pyenv/bin/pyenv install "$PYVER"
fi

# move python install path
PYPATH="$SCRIPT_PATH/$APP_NAME.app/Contents/Frameworks/python"
mkdir "$PYPATH"
cp -a ~/.pyenv/versions/"$PYVER" "$PYPATH"
PYTHON="$PYPATH/$PYVER/bin/python"

# remove pyc because they contain absolute paths
find -E "$PYPATH/$PYVER" -regex '.*.pyc' | grep -v "opt-2.pyc" | xargs rm  # todo: fix

rm -rf "$PYPATH/$PYVER/share"
rm -rf "$PYPATH/$PYVER/lib/python${PYVER:0:3}"/{test,unittest/test,turtledemo,tkinter}
pushd "$APP_NAME.app/Contents/Frameworks"

echo "-- Copy frameworks"

if [ "$USE_GSTREAMER" != "0" ]; then
    cp -a /Library/Frameworks/GStreamer.framework .
fi
cp -a /Library/Frameworks/SDL2.framework .
cp -a /Library/Frameworks/SDL2_image.framework .
cp -a /Library/Frameworks/SDL2_ttf.framework .
cp -a /Library/Frameworks/SDL2_mixer.framework .
mkdir ../lib/

echo "-- Reduce frameworks size"
rm -rf {SDL2,SDL2_image,SDL2_ttf,SDL2_mixer}.framework/Headers
rm -rf {SDL2,SDL2_image,SDL2_ttf,SDL2_mixer}.framework/Versions/A/Headers
rm -rf SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/A/Headers
rm -rf SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/Current
cd SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/
rm -rf Current
ln -s A Current
cd -
rm -rf SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Headers
if [ "$USE_GSTREAMER" != "0" ]; then
    rm -rf GStreamer.framework/Headers
    rm -rf GStreamer.framework/Versions/1.0/share/locale
    rm -rf GStreamer.framework/Versions/1.0/lib/gstreamer-1.0/static
    rm -rf GStreamer.framework/Versions/1.0/share/gstreamer-1.0/validate-scenario
    rm -rf GStreamer.framework/Versions/1.0/share/fontconfig/conf.avail
    rm -rf GStreamer.framework/Versions/1.0/include
    rm -rf GStreamer.framework/Versions/1.0/lib/gst-validate-launcher
    rm -rf GStreamer.framework/Versions/1.0/Headers
    rm -rf GStreamer.framework/Versions/1.0/lib/pkgconfig
    rm -rf GStreamer.framework/Versions/1.0/bin
    rm -rf GStreamer.framework/Versions/1.0/etc
    rm -rf GStreamer.framework/Versions/1.0/share/gstreamer
fi
find -E . -regex '.*\.a$' -exec rm {} \;
find -E . -regex '.*\.la$' -exec rm {} \;
find -E . -regex '.*\.exe$' -exec rm {} \;

if [ "$USE_GSTREAMER" != "0" ]; then
    echo "-- Remove duplicate gstreamer libraries"
    $PYTHON "$SCRIPT_PATH/data/link_duplicate.py" GStreamer.framework/Libraries
fi

echo "-- Remove broken symlink"
find . -type l -exec sh -c "file -b {} | grep -q ^broken" \; -print
find . -type l -exec sh -c "file -b {} | grep -q ^broken" \; -print | xargs rm

if [ "$USE_GSTREAMER" != "0" ]; then
  echo "-- Copy gst-plugin-scanner"
  mv GStreamer.framework/Versions/Current/libexec/gstreamer-1.0/gst-plugin-scanner ../Resources
fi

popd

# --- Python resources

pushd "$APP_NAME.app/Contents/Resources/"

echo "-- Create a virtualenv"
$PYTHON -m pip install --upgrade pip virtualenv
$PYTHON -m virtualenv venv

echo "-- Install dependencies"
source venv/bin/activate

./venv/bin/python -m pip install git+https://github.com/tito/osxrelocator
export USE_SDL2=1
./venv/bin/python -m pip install "kivy[base] @ $KIVY_PATH"
echo "-- Link python to the right location for relocation"
ln -s ./venv/bin/python ./python

popd

# --- Relocation

echo "-- Relocate frameworks"
pushd "$APP_NAME.app"
osxrelocator -r . /usr/local/lib/ \
    @executable_path/../lib/
if [ "$USE_GSTREAMER" != "0" ]; then
    osxrelocator -r . /Library/Frameworks/GStreamer.framework/ \
        @executable_path/../Frameworks/GStreamer.framework/
fi
osxrelocator -r . /Library/Frameworks/SDL2/ \
    @executable_path/../Frameworks/SDL2/
osxrelocator -r . /Library/Frameworks/SDL2_ttf/ \
    @executable_path/../Frameworks/SDL2_ttf/
osxrelocator -r . /Library/Frameworks/SDL2_image/ \
    @executable_path/../Frameworks/SDL2_image/
osxrelocator -r . @rpath/SDL2.framework/Versions/A/SDL2 \
    @executable_path/../Frameworks/SDL2.framework/Versions/A/SDL2
osxrelocator -r . @rpath/SDL2_ttf.framework/Versions/A/SDL2_ttf \
    @executable_path/../Frameworks/SDL2_ttf.framework/Versions/A/SDL2_ttf
osxrelocator -r . @rpath/SDL2_image.framework/Versions/A/SDL2_image \
    @executable_path/../Frameworks/SDL2_image.framework/Versions/A/SDL2_image
osxrelocator -r . @rpath/SDL2_mixer.framework/Versions/A/SDL2_mixer \
    @executable_path/../Frameworks/SDL2_mixer.framework/Versions/A/SDL2_mixer
osxrelocator -r . ~/.pyenv/versions/"$PYVER"/openssl/lib/ \
    @executable_path/../Frameworks/python/"$PYVER"/openssl/lib
popd

echo "-- Relocate virtualenv"
pushd "$APP_NAME.app/Contents/Resources/venv"

rm bin/activate.csh
rm bin/activate.fish

pushd bin
rm ./python ./python3
ln -s "../../../Frameworks/python/$PYVER/bin/python" .
ln -s "../../../Frameworks/python/$PYVER/bin/python3" .

sed -E -i '.bak' 's#^VIRTUAL_ENV=.*#VIRTUAL_ENV=$(cd $(dirname "$BASH_SOURCE"); dirname `pwd`)#' activate

popd
popd

chmod +x relocate.sh
./relocate.sh "$APP_NAME.app"

echo "-- Done !"
