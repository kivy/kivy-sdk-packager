#!/bin/bash

VERSION=stable

set -x  # verbose
set -e  # exit on error

PLATYPUS=/usr/local/bin/platypus
SCRIPT_PATH="${BASH_SOURCE[0]}";
if([ -h "${SCRIPT_PATH}" ]) then
  while([ -h "${SCRIPT_PATH}" ]) do SCRIPT_PATH=`readlink "${SCRIPT_PATH}"`; done
fi
SCRIPT_PATH=$(python -c "import os; print os.path.realpath(os.path.dirname('${SCRIPT_PATH}'))")
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

# --- Frameworks

echo "-- Create Frameworks directory"
mkdir -p Kivy.app/Contents/Frameworks
pushd Kivy.app/Contents/Frameworks

echo "-- Copy frameworks"
cp -a /Library/Frameworks/GStreamer.framework .
cp -a /Library/Frameworks/SDL2.framework .
cp -a /Library/Frameworks/SDL2_image.framework .
cp -a /Library/Frameworks/SDL2_ttf.framework .
cp -a /Library/Frameworks/SDL2_mixer.framework .

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

echo "-- Remove duplicate gstreamer libraries"
python "$SCRIPT_PATH/data/link_duplicate.py" GStreamer.framework/Libraries

echo "-- Remove broken symlink"
find . -type l -exec sh -c "file -b {} | grep -q ^broken" \; -print
find . -type l -exec sh -c "file -b {} | grep -q ^broken" \; -print | xargs rm

echo "-- Copy gst-plugin-scanner"
mv GStreamer.framework/Versions/Current/libexec/gstreamer-1.0/gst-plugin-scanner ../Resources

popd

# --- Python resources

pushd Kivy.app/Contents/Resources/

echo "-- Create a virtualenv"
virtualenv -p /System/Library/Frameworks/Python.framework/Versions/2.7/Resources/Python.app/Contents/MacOS/Python venv

echo "-- Install dependencies"
source venv/bin/activate
pip install cython==0.21.2
pip install pygments docutils
pip install osxrelocator

echo "-- Link python to the right location for relocation"
ln -s venv/bin/python .

popd

# --- Kivy

echo "-- Download and compile Kivy"
pushd Kivy.app/Contents/Resources
curl -L -O https://github.com/kivy/kivy/archive/$VERSION.zip
unzip $VERSION.zip
rm $VERSION.zip
mv kivy-$VERSION kivy

cd kivy
USE_SDL2=1 make

popd

# --- Relocation

echo "-- Relocate frameworks"
pushd Kivy.app
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
popd

# relocate the activate script
echo "-- Relocate virtualenv"
pushd Kivy.app/Contents/Resources/venv
virtualenv --relocatable .
gsed -i -r 's#^VIRTUAL_ENV=.*#VIRTUAL_ENV=$(cd $(dirname "$BASH_SOURCE"); dirname `pwd`)#' bin/activate
rm bin/activate.csh
rm bin/activate.fish

echo "-- Done !"
