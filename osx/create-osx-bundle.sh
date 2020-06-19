#!/bin/bash

USAGE="Usage::

    create-osx-bundle.sh <Kivy version> <Python version>

For Example::

    sh ./create-osx-bundle.sh 1.11.1 3.7.4
"

# -- VERSION=1.11.1
if [ "x$1" != "x" ]; then
    VERSION=$1
else
    echo "$USAGE"
    exit 1
fi

echo "Using kivy version $VERSION"

# -- PYVER=3.7.4

if [ "x$2" != "x" ]; then
    PYVER=$2
else
    echo "$USAGE"
    exit 1
fi

echo "Using Python version $PYVER"

set -x  # verbose
set -e  # exit on error

PLATYPUS=/usr/local/bin/platypus
SCRIPT_PATH="${BASH_SOURCE[0]}";

PYTHON=python

if([ -h "${SCRIPT_PATH}" ]) then
  while([ -h "${SCRIPT_PATH}" ]) do SCRIPT_PATH=`readlink "${SCRIPT_PATH}"`; done
fi

SCRIPT_PATH=$(python -c "import os; print(os.path.realpath(os.path.dirname('${SCRIPT_PATH}')))")
OSXRELOCATOR="osxrelocator"
echo "-- Create initial Kivy.app package"
$PLATYPUS -DBR -x -y \
    -i "$SCRIPT_PATH/data/icon.icns" \
    -a "Kivy" \
    -o "None" \
    -p "/bin/bash" \
    -V "$VERSION" \
    -I "org.kivy.osxlauncher" \
    -X "*" \
    "$SCRIPT_PATH/data/script" \
    "$SCRIPT_PATH/Kivy.app"



echo "--- Frameworks"

echo "-- Create Frameworks directory"
mkdir -p Kivy.app/Contents/Frameworks
if [ ! -f ~/.pyenv/bin/pyenv ]; then
  curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
  ~/.pyenv/bin/pyenv install $PYVER
fi
PYPATH="$SCRIPT_PATH/Kivy.app/Contents/Frameworks/python"
mkdir "$PYPATH"
cp -a ~/.pyenv/versions/$PYVER "$PYPATH"
find -E "$PYPATH/$PYVER" -regex '.*.pyc' | grep -v "opt-2.pyc" | xargs rm
PYTHON="$PYPATH/$PYVER/bin/python"
rm -rf python/$PYVER/share
rm -rf python/$PYVER/lib/python${PYVER[@]:0:3}/{test,unittest/test,turtledemo,tkinter}
pushd Kivy.app/Contents/Frameworks

echo "-- Copy frameworks"
cp -a /Library/Frameworks/GStreamer.framework .
cp -a /Library/Frameworks/SDL2.framework .
cp -a /Library/Frameworks/SDL2_image.framework .
cp -a /Library/Frameworks/SDL2_ttf.framework .
cp -a /Library/Frameworks/SDL2_mixer.framework .
mkdir ../lib/

echo "-- Reduce frameworks size"
rm -rf {SDL2,SDL2_image,SDL2_ttf,SDL2_mixer,GStreamer}.framework/Headers
rm -rf {SDL2,SDL2_image,SDL2_ttf,SDL2_mixer}.framework/Versions/A/Headers
rm -rf SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/A/Headers
rm -rf SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/Current
cd SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/
rm -rf Current
ln -s A Current
cd -
rm -rf SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Headers
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
find -E . -regex '.*\.a$' -exec rm {} \;
find -E . -regex '.*\.la$' -exec rm {} \;
find -E . -regex '.*\.exe$' -exec rm {} \;

echo "-- Remove duplicate gstreamer libraries"
$PYTHON $SCRIPT_PATH/data/link_duplicate.py GStreamer.framework/Libraries

echo "-- Remove broken symlink"
find . -type l -exec sh -c "file -b {} | grep -q ^broken" \; -print
find . -type l -exec sh -c "file -b {} | grep -q ^broken" \; -print | xargs rm

echo "-- Copy gst-plugin-scanner"
mv GStreamer.framework/Versions/Current/libexec/gstreamer-1.0/gst-plugin-scanner ../Resources

popd

# --- Python resources

pushd Kivy.app/Contents/Resources/

echo "-- Create a virtualenv"
if [ ${PYVER[@]:0:1} = 3 ]; then
    $PYTHON -m venv venv
else
    $PYTHON -m pip install virtualenv
    $PYTHON -m virtualenv venv
fi

echo "-- Install dependencies"
source venv/bin/activate
#curl -O -L https://github.com/cython/cython/archive/0.28.1.zip && venv/bin/pip install 0.28.1.zip && rm 0.28.1.zip
#curl -O -L https://github.com/sol/pygments/archive/2.2.0.zip && venv/bin/pip install 2.2.0.zip && rm 2.2.0.zip
#curl -O -L https://github.com/docutils-mirror/docutils/archive/0.12.zip && venv/bin/pip install 0.12.zip && rm 0.12.zip
curl -OL http://bootstrap.pypa.io/get-pip.py
./venv/bin/python get-pip.py
./venv/bin/python -m pip install virtualenv==16.7.10
./venv/bin/python -m pip install pygments
./venv/bin/python -m pip install cython==0.28.2
./venv/bin/python -m pip install docutils
./venv/bin/python -m pip install git+https://github.com/tito/osxrelocator
echo "-- Link python to the right location for relocation"
ln -s ./venv/bin/python ./python

popd

# --- Kivy

echo "-- Download and compile Kivy"
pushd Kivy.app/Contents/Resources
curl -L -O https://github.com/kivy/kivy/archive/$VERSION.zip
unzip $VERSION.zip
rm $VERSION.zip
mv kivy-$VERSION kivy

cd kivy
USE_SDL2=1 ../venv/bin/python setup.py build_ext --inplace
popd

# --- Relocation

echo "-- Relocate frameworks"
pushd Kivy.app
osxrelocator -r . /usr/local/lib/ \
    @executable_path/../lib/
osxrelocator -r . /Library/Frameworks/GStreamer.framework/ \
    @executable_path/../Frameworks/GStreamer.framework/
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
osxrelocator -r . ~/.pyenv/versions/3.6.5/openssl/lib/ \
    @executable_path/../Frameworks/python/3.6.5/openssl/lib
popd

# relocate the activate script
echo "-- Relocate virtualenv"
pushd Kivy.app/Contents/Resources/venv
virtualenv --relocatable .
sed -i -r 's#^VIRTUAL_ENV=.*#VIRTUAL_ENV=$(cd $(dirname "$BASH_SOURCE"); dirname `pwd`)#' bin/activate
rm bin/activate.csh
rm bin/activate.fish
popd

pushd Kivy.app/Contents/Resources/venv/bin/
rm ./python
ln -s ../../../Frameworks/python/$PYVER/bin/python .
echo "-- Done !"
