#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Creates a Kivy bundle that can be used to build your app into a dmg. See documentation.

Usage: create-osx-bundle.sh [options]

    -k --kivy     <Kivy version or path, default:master>  The local path to Kivy source or a git tag/branch/commit.
    -p --python   <Python version, default:3.8.5>         The Python version to use.
    -n --name     <App name, default:Kivy>                The name of the app.
    -v --version  <App version, default:master>           The version of the app.
    -a --author   <Author, default:Kivy Developers>       The author name.
    -o --org      <org, default:org.kivy.osxlauncher>     The org id used for the app.
    -i --icon     <icon, default:data/icon.icns>          A icns icon file path.
    -s --script   <app_main_script, default:data/script>  The script to run when the user clicks the app.
    -g --gstreamer<using gstreamer, default:1>            Whether to include gstreamer. Must be one of 1 or 0.

Requirements::

    The SDL2, SDL2_image, SDL2_ttf, and SDL2_mixer frameworks needs to be installed.
    If gstreamer is enabled (the default), gstreamer-1.0 also need to be installed.

    Platypus also needs to be installed. Finally, any python3 version must be available for
    initial scripting.
"

KIVY_PATH="master"
PYVER="3.8.5"
APP_NAME="Kivy"
APP_VERSION="master"
AUTHOR="Kivy Developers"
APP_ORG="org.kivy.osxlauncher"
ICON_PATH="data/icon.icns"
APP_SCRIPT="data/script"
USE_GSTREAMER="1"

while [[ "$#" -gt 0 ]]; do
    # empty arg?
    if [ -z "$2" ]; then
        echo "$USAGE"
        exit 1
    fi

    case $1 in
        -k|--kivy) KIVY_PATH="$2";;
        -p|--python) PYVER="$2";;
        -n|--name) APP_NAME="$2";;
        -v|--version) APP_VERSION="$2";;
        -a|--author) AUTHOR="$2";;
        -o|--org) APP_ORG="$2";;
        -i|--icon) ICON_PATH="$2";;
        -s|--script) APP_SCRIPT="$2";;
        -g|--gstreamer) USE_GSTREAMER="$2";;
        *) echo "Unknown parameter passed: $1"; echo "$USAGE"; exit 1 ;;
    esac
    shift; shift
done

# get kivy path or url
if [ -d "$KIVY_PATH" ]; then
    # get full path
    pushd "$KIVY_PATH"
    KIVY_PATH="$(pwd)"
    popd
else
    KIVY_PATH="https://github.com/kivy/kivy/archive/$KIVY_PATH.zip"
fi

echo "Using Kivy $KIVY_PATH"
echo "Using Python version $PYVER"
echo "Build $APP_NAME version $APP_VERSION org $APP_ORG by $AUTHOR"
echo "App will launch with $APP_SCRIPT using icon $ICON_PATH"

PLATYPUS=/usr/local/bin/platypus
if [ ! -f "$PLATYPUS" ]; then
    echo "Could not find platypus at $PLATYPUS"
    exit 1
fi

SCRIPT_PATH="${BASH_SOURCE[0]}"
PYTHON=python3

# follow any symbolic links
if [ -h "${SCRIPT_PATH}" ]; then
  while [ -h "${SCRIPT_PATH}" ]; do
      SCRIPT_PATH=$(readlink "${SCRIPT_PATH}")
  done
fi

SCRIPT_PATH=$($PYTHON -c "import os; print(os.path.realpath(os.path.dirname('$SCRIPT_PATH')))")


echo "-- Create initial $APP_NAME.app package"
$PLATYPUS -DBR -y \
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
if [ ! -d "/Library/Frameworks/Python.framework/Versions/${PYVER:0:3}" ]; then
    curl -L -O "https://www.python.org/ftp/python/$PYVER/python-$PYVER-macosx10.9.pkg"
    sudo installer -pkg "python-$PYVER-macosx10.9.pkg" -target /
fi
SRC_PYTHON="/Library/Frameworks/Python.framework/Versions/${PYVER:0:3}/bin/python3"

echo "-- Copy frameworks"

pushd "$APP_NAME.app/Contents/Frameworks"

cp -a "/Library/Frameworks/Python.framework" .
if [ "$USE_GSTREAMER" != "0" ]; then
    cp -a /Library/Frameworks/GStreamer.framework .
fi
cp -a /Library/Frameworks/SDL2.framework .
cp -a /Library/Frameworks/SDL2_image.framework .
cp -a /Library/Frameworks/SDL2_ttf.framework .
cp -a /Library/Frameworks/SDL2_mixer.framework .
mkdir ../lib/

chmod -R 775 .

echo "-- Reduce frameworks size"

# remove pyc because they contain absolute paths
find "Python.framework/" -name "*.pyc" -print0 | xargs -0 rm

rm -rf "Python.framework/Versions/${PYVER:0:3}"/{share,Headers}
rm -rf "Python.framework/Versions/${PYVER:0:3}/Resources"/{*.lproj,Info.plist}
rm -rf "Python.framework/Versions/${PYVER:0:3}/Resources/Python.app/Contents/"{Resources,Info.plist,PkgInfo}

rm -rf {SDL2,SDL2_image,SDL2_ttf,SDL2_mixer}.framework/Headers
rm -rf {SDL2,SDL2_image,SDL2_ttf,SDL2_mixer}.framework/Versions/A/Headers
rm -rf SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/A/Headers
rm -rf SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/Current

pushd SDL2_ttf.framework/Versions/A/Frameworks/FreeType.framework/Versions/
rm -rf Current
ln -s A Current
popd

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
    $SRC_PYTHON "$SCRIPT_PATH/data/link_duplicate.py" GStreamer.framework/Libraries
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
$SRC_PYTHON -m pip install --upgrade pip virtualenv --user
$SRC_PYTHON -m virtualenv venv

echo "-- Install dependencies"
source venv/bin/activate

./venv/bin/python -m pip install git+https://github.com/tito/osxrelocator
export USE_SDL2=1
export USE_GSTREAMER="$USE_GSTREAMER"
if [ -d "$KIVY_PATH" ]; then
    ./venv/bin/python -m pip install "${KIVY_PATH}[base]"
else
    ./venv/bin/python -m pip install "kivy[base] @ $KIVY_PATH"
fi
echo "-- Link python to the right location for relocation"
ln -s ./venv/bin/python ./python
ln -s ./venv/bin/python ./python3

cp ../../../data/kivy_activate "venv/bin"

popd

# --- Relocation
echo "-- Relocate virtualenv"
pushd "$APP_NAME.app/Contents/Resources/venv"

rm bin/activate.csh
rm bin/activate.fish

pushd bin
rm -f ./python ./python3 ./python3.*
ln -s ../../../Frameworks/Python.framework/Versions/3*/bin/python"${PYVER:0:3}" python
ln -s ../../../Frameworks/Python.framework/Versions/3*/bin/python"${PYVER:0:3}" python3
ln -s ../../../Frameworks/Python.framework/Versions/3*/bin/python"${PYVER:0:3}" "python${PYVER:0:3}"

# fix path
sed -E -i '.bak' 's#^VIRTUAL_ENV=.*#VIRTUAL_ENV=$(cd $(dirname "$BASH_SOURCE"); dirname `pwd`)#' activate
# fix PYTHONHOME
sed -i '.bak' 's#if ! \[ -z "\${PYTHONHOME+_}" ] ; then#if [ "_" ] ; then#' activate
sed -E -i '.bak' 's#unset PYTHONHOME$#export PYTHONHOME="$(cd "$(dirname "$BASH_SOURCE")"/../../../Frameworks/Python.framework/Versions/3*; echo "$(pwd)")"#' activate
rm -f ./*.bak

popd
popd

./relocate.sh "$APP_NAME.app"

echo "-- Relocate frameworks"
pushd "$APP_NAME.app"

# it's not clear where executable_path is. The way python works on osx
# is that /Python.framework/Versions/3.x/Python actually launches internally
# Python.framework/Versions/3.8/Resources/Python.app/Contents/MacOS/Python. And then we
# also have the venv's python. So which of them are the executable_path?
#
# It seems that sometimes it is the venv's python, but it could also be
# Python.app/Contents/MacOS/Python. So we create a symlink next to each python pointing to
# Contents/ so we can simply do @executable_path/Contents/... and it will always work.
# maybe in the future we can make sure which one it is and reduce the need for the multiple symlinks.
pushd "Contents/Frameworks/Python.framework/Versions/${PYVER:0:3}/Resources/Python.app/Contents/MacOS/"
ln -s ../../../../../../../../../Contents Contents
popd
pushd "Contents/Resources/venv/bin"
ln -s ../../../../Contents Contents
popd
pushd "Contents/Frameworks/Python.framework/Versions/${PYVER:0:3}/"
ln -s ../../../../../Contents Contents
popd

osxrelocator -r . /usr/local/lib/ \
    @executable_path/Contents/lib/
echo "Done relocating lib"

if [ "$USE_GSTREAMER" != "0" ]; then
    # Additionally, we get the following error if the fixed path is too long, so make sure it's short.
    # we get install_name_tool: changing install names or rpaths can't be redone for: GStreamer.framework/Versions/1.0/GStreamer
    # (for architecture x86_64) because larger updated load commands do not fit
    # (the program must be relinked, and you may need to use -headerpad or -headerpad_max_install_names)
    # so use symlink to make path shorter
    pushd Contents
    ln -s Frameworks/GStreamer.framework/Versions/1.0 GSt1.0
    popd
    pushd Contents/Resources
    # gst-plugin-scanner is looking for dylib relative to itself, so we need to add another
    # Contents symlink next to it.
    ln -s ../../Contents Contents
    popd
    osxrelocator -r . /Library/Frameworks/GStreamer.framework/Versions/1.0 \
        @executable_path/Contents/GSt1.0
    osxrelocator -r . @rpath/GStreamer.framework/Versions/1.0/GStreamer \
        @executable_path/Contents/GSt1.0/GStreamer
    echo "Done relocating gstreamer"
fi
osxrelocator -r . /Library/Frameworks/SDL2/ \
    @executable_path/Contents/Frameworks/SDL2/
osxrelocator -r . /Library/Frameworks/SDL2_ttf/ \
    @executable_path/Contents/Frameworks/SDL2_ttf/
osxrelocator -r . /Library/Frameworks/SDL2_image/ \
    @executable_path/Contents/Frameworks/SDL2_image/
osxrelocator -r . /Library/Frameworks/SDL2_mixer/ \
    @executable_path/Contents/Frameworks/SDL2_mixer/
echo "Done relocating SDL2"

osxrelocator -r . @rpath/SDL2.framework/Versions/A/SDL2 \
    @executable_path/Contents/Frameworks/SDL2.framework/Versions/A/SDL2
osxrelocator -r . @rpath/SDL2_ttf.framework/Versions/A/SDL2_ttf \
    @executable_path/Contents/Frameworks/SDL2_ttf.framework/Versions/A/SDL2_ttf
osxrelocator -r . @rpath/SDL2_image.framework/Versions/A/SDL2_image \
    @executable_path/Contents/Frameworks/SDL2_image.framework/Versions/A/SDL2_image
osxrelocator -r . @rpath/SDL2_mixer.framework/Versions/A/SDL2_mixer \
    @executable_path/Contents/Frameworks/SDL2_mixer.framework/Versions/A/SDL2_mixer
echo "Done relocating SDL2 rpath"

osxrelocator -r . /Library/Frameworks/Python \
    @executable_path/Contents/Frameworks/Python
# Python.app/Contents/MacOS/Python should link to Python.framework/Versions/${PYVER:0:3}/Python,
# which this fixes
osxrelocator -r . @rpath/Python.framework/Versions/"${PYVER:0:3}"/Python \
    @executable_path/Contents/Frameworks/Python.framework/Versions/"${PYVER:0:3}"/Python
echo "Done relocating Python"

# for some reason Python.framework/Versions/3.x/bin/python3.x originally links to
# /Library/Frameworks/Python.framework/Versions/3.x/Python, but it needs to be updated to
# Frameworks/Python.framework/Python (which seems to be a link to
# Frameworks/Python.framework/Versions/Current/Python).
install_name_tool -change "/Library/Frameworks/Python.framework/Versions/${PYVER:0:3}/Python" \
  "@executable_path/Contents/Frameworks/Python.framework/Python" \
  "Contents/Frameworks/Python.framework/Versions/${PYVER:0:3}/bin/python${PYVER:0:3}"

codesign -fs - "Contents/Frameworks/Python.framework/Versions/${PYVER:0:3}/Python"

popd

echo "-- Done !"
