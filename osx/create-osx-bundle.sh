#!/bin/bash
set -x # verbose
set -e # exit on error

USAGE="Creates a Kivy bundle that can be used to build your app into a dmg. See documentation.

Usage: create-osx-bundle.sh [options]

    -k --kivy     <Kivy version or path, default:master>  The local path to Kivy source or a git tag/branch/commit.
    -e --extras   <Kivy extras selection, default:base>   The extras selection (base, full, dev ...).
    -p --python   <Python version, default:3.9.9>         The Python version to use.
    -n --name     <App name, default:Kivy>                The name of the app.
    -v --version  <App version, default:master>           The version of the app.
    -a --author   <Author, default:Kivy Developers>       The author name.
    -o --org      <org, default:org.kivy.osxlauncher>     The org id used for the app.
    -i --icon     <icon, default:data/icon.icns>          A icns icon file path.
    -s --script   <app_main_script, default:data/script>  The script to run when the user clicks the app.

Requirements::
    Platypus  needs to be installed. Finally, any python3 version must be available for
    initial scripting.
"

KIVY_PATH="master"
EXTRAS="base"
PYVER="3.9.9"
OPENSSL_VERSION="1.1.1l"
SDL_VERSION="release-2.0.20"
SDL_IMAGE_VERSION="168ceb577c245c91801c1bcaf970ef31c9b4d7ba"
SDL_MIXER_VERSION="64120a41f62310a8be9bb97116e15a95a892e39d"
SDL_TTF_VERSION="release-2.0.18"
APP_NAME="Kivy"
APP_VERSION="master"
AUTHOR="Kivy Developers"
APP_ORG="org.kivy.osxlauncher"
ICON_PATH="data/icon.icns"
APP_SCRIPT="data/script"

while [[ "$#" -gt 0 ]]; do
    # empty arg?
    if [ -z "$2" ]; then
        echo "$USAGE"
        exit 1
    fi

    case $1 in
    -k | --kivy) KIVY_PATH="$2" ;;
    -e | --extras) EXTRAS="$2" ;;
    -p | --python) PYVER="$2" ;;
    -n | --name) APP_NAME="$2" ;;
    -v | --version) APP_VERSION="$2" ;;
    -a | --author) AUTHOR="$2" ;;
    -o | --org) APP_ORG="$2" ;;
    -i | --icon) ICON_PATH="$2" ;;
    -s | --script) APP_SCRIPT="$2" ;;
    *)
        echo "Unknown parameter passed: $1"
        echo "$USAGE"
        exit 1
        ;;
    esac
    shift
    shift
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

git clone "https://github.com/sveinbjornt/Platypus"

pushd Platypus
git checkout $PLATYPUS
export MACOSX_DEPLOYMENT_TARGET=10.9
./build_release.sh
popd

mkdir -p /usr/local/bin
mkdir -p /usr/local/share/platypus
cp Platypus/products/platypus_clt /usr/local/bin/platypus
cp Platypus/products/ScriptExec.app/Contents/MacOS/ScriptExec /usr/local/share/platypus/ScriptExec
cp -a Platypus/products/Platypus.app/Contents/Resources/MainMenu.nib /usr/local/share/platypus/MainMenu.nib
chmod -R 755 /usr/local/share/platypus

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

echo "-- Clean previous build (if any) and move to build folder"
rm -rf build
mkdir build

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
    "$SCRIPT_PATH/build/$APP_NAME.app"

# Platypus? sets non-blocking mode. That was leading to an error during openssl or python3 build.
$PYTHON -c "import fcntl; fcntl.fcntl(1, fcntl.F_SETFL, 0)"

echo "-- Entering build folder"
pushd build

echo "-- Create $APP_NAME.app/Contents/Frameworks directory"
mkdir -p "$APP_NAME.app/Contents/Frameworks"

echo "-- Download needed files"
curl -L -O "http://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz"
curl -L -O "https://www.python.org/ftp/python/${PYVER}/Python-${PYVER}.tgz"
curl -L -O "https://github.com/libsdl-org/SDL/archive/refs/tags/${SDL_VERSION}.tar.gz"
curl -L -O "https://github.com/libsdl-org/SDL_mixer/archive/${SDL_MIXER_VERSION}.tar.gz"
curl -L -O "https://github.com/libsdl-org/SDL_image/archive/${SDL_IMAGE_VERSION}.tar.gz"
curl -L -O "https://github.com/libsdl-org/SDL_ttf/archive/refs/tags/${SDL_TTF_VERSION}.tar.gz"

echo "-- Set MACOSX_DEPLOYMENT_TARGET=10.9"
export SDKROOT=$(xcrun -sdk macosx --show-sdk-path)
export MACOSX_DEPLOYMENT_TARGET=10.9

echo "-- Build SDL2 (Universal)"
tar -xvf "${SDL_VERSION}.tar.gz"
mv "SDL-${SDL_VERSION}" "SDL"
pushd "SDL"
xcodebuild ONLY_ACTIVE_ARCH=NO -project Xcode/SDL/SDL.xcodeproj -target Framework -configuration Release
popd

echo "-- Copy SDL2.framework to ${APP_NAME}.app/Contents/Frameworks"
cp -R SDL/Xcode/SDL/build/Release/SDL2.framework "${APP_NAME}.app/Contents/Frameworks"

echo "-- Build SDL2_mixer (Universal)"
tar -xvf "${SDL_MIXER_VERSION}.tar.gz"
mv "SDL_mixer-${SDL_MIXER_VERSION}" "SDL_mixer"
pushd "SDL_mixer"
xcodebuild ONLY_ACTIVE_ARCH=NO \
        "HEADER_SEARCH_PATHS=\$HEADER_SEARCH_PATHS ${SCRIPT_PATH}/build/${APP_NAME}.app/Contents/Frameworks/SDL2.framework/Headers" \
        "FRAMEWORK_SEARCH_PATHS=\$FRAMEWORK_SEARCH_PATHS ${SCRIPT_PATH}/build/${APP_NAME}.app/Contents/Frameworks" \
        -project Xcode/SDL_mixer.xcodeproj -target Framework -configuration Release
popd

echo "-- Copy SDL2_mixer.framework to ${APP_NAME}.app/Contents/Frameworks"
cp -R SDL_mixer/Xcode/build/Release/SDL2_mixer.framework "${APP_NAME}.app/Contents/Frameworks"

echo "-- Build SDL2_image (Universal)"
tar -xvf "${SDL_IMAGE_VERSION}.tar.gz"
mv "SDL_image-${SDL_IMAGE_VERSION}" "SDL_image"
pushd "SDL_image"
xcodebuild ONLY_ACTIVE_ARCH=NO \
        "HEADER_SEARCH_PATHS=\$HEADER_SEARCH_PATHS ${SCRIPT_PATH}/build/${APP_NAME}.app/Contents/Frameworks/SDL2.framework/Headers" \
        "FRAMEWORK_SEARCH_PATHS=\$FRAMEWORK_SEARCH_PATHS ${SCRIPT_PATH}/build/${APP_NAME}.app/Contents/Frameworks" \
        -project Xcode/SDL_image.xcodeproj -target Framework -configuration Release
popd

echo "-- Copy SDL2_image.framework to ${APP_NAME}.app/Contents/Frameworks"
cp -R SDL_image/Xcode/build/Release/SDL2_image.framework "${APP_NAME}.app/Contents/Frameworks"

echo "-- Build SDL2_ttf (Universal)"
tar -xvf "${SDL_TTF_VERSION}.tar.gz"
mv "SDL_ttf-${SDL_TTF_VERSION}" "SDL_ttf"
pushd "SDL_ttf"
xcodebuild ONLY_ACTIVE_ARCH=NO \
        "HEADER_SEARCH_PATHS=\$HEADER_SEARCH_PATHS ${SCRIPT_PATH}/build/${APP_NAME}.app/Contents/Frameworks/SDL2.framework/Headers" \
        "FRAMEWORK_SEARCH_PATHS=\$FRAMEWORK_SEARCH_PATHS ${SCRIPT_PATH}/build/${APP_NAME}.app/Contents/Frameworks" \
        -project Xcode/SDL_ttf.xcodeproj -target Framework -configuration Release
popd

echo "-- Copy SDL2_ttf.framework to ${APP_NAME}.app/Contents/Frameworks"
cp -R SDL_ttf/Xcode/build/Release/SDL2_ttf.framework "${APP_NAME}.app/Contents/Frameworks"

echo "-- Build OpenSSL (x86_64)"
tar -xvf "openssl-${OPENSSL_VERSION}.tar.gz"
mv "openssl-${OPENSSL_VERSION}" "openssl-${OPENSSL_VERSION}_x86_64"
pushd "openssl-${OPENSSL_VERSION}_x86_64"
./Configure darwin64-x86_64-cc
make clean
make build_libs
popd

echo "-- Build OpenSSL (arm64)"
tar -xvf "openssl-${OPENSSL_VERSION}.tar.gz"
mv "openssl-${OPENSSL_VERSION}" "openssl-${OPENSSL_VERSION}_arm64"
pushd "openssl-${OPENSSL_VERSION}_arm64"
./Configure darwin64-arm64-cc
make clean
make build_libs
popd

echo "-- Merge OpenSSL libs to a fat library and copy include folder"
mkdir openssl
cp -R "openssl-${OPENSSL_VERSION}_x86_64/include" "openssl/include"
mkdir openssl/lib
lipo "openssl-${OPENSSL_VERSION}_x86_64/libcrypto.a" "openssl-${OPENSSL_VERSION}_arm64/libcrypto.a" -create -output "openssl/lib/libcrypto.a"
lipo "openssl-${OPENSSL_VERSION}_x86_64/libssl.a" "openssl-${OPENSSL_VERSION}_arm64/libssl.a" -create -output "openssl/lib/libssl.a"

echo "-- Build python from scratch"
KIVY_APP_PYTHON_PREFIX="${SCRIPT_PATH}/build/${APP_NAME}.app/Contents/Resources/python3"
KIVY_APP_PYTHON_BIN="${KIVY_APP_PYTHON_PREFIX}/bin/python3"
tar -xvf "Python-${PYVER}.tgz"
pushd "Python-${PYVER}"
./configure --prefix=$KIVY_APP_PYTHON_PREFIX --enable-universalsdk --disable-test-modules --with-universal-archs=universal2 --with-openssl=../openssl
make
make install
popd

echo "-- Create a virtualenv in ${APP_NAME}.app/Contents/Resources"
pushd "$APP_NAME.app/Contents/Resources/"
$KIVY_APP_PYTHON_BIN -m pip install --upgrade pip virtualenv --user
$KIVY_APP_PYTHON_BIN -m virtualenv venv

echo "-- Activate the just created virtualenv"
source venv/bin/activate
popd

echo "-- Build kivy from scratch"
export KIVY_SDL2_FRAMEWORKS_SEARCH_PATH="${SCRIPT_PATH}/build/${APP_NAME}.app/Contents/Frameworks"
python3 -m pip install Cython
if [ -d "$KIVY_PATH" ]; then
    python3 -m pip install "${KIVY_PATH}[${EXTRAS}]"
else
    python3 -m pip install "kivy[${EXTRAS}] @ $KIVY_PATH"
fi

echo "-- Relocate SDL2 frameworks"
pushd $APP_NAME.app
python3 -m pip install git+https://github.com/tito/osxrelocator
osxrelocator -r . @rpath/SDL2.framework/Versions/A/SDL2 @executable_path/../../../../Contents/Frameworks/SDL2.framework/Versions/A/SDL2
osxrelocator -r . @rpath/SDL2_ttf.framework/Versions/A/SDL2_ttf @executable_path/../../../../Contents/Frameworks/SDL2_ttf.framework/Versions/A/SDL2_ttf
osxrelocator -r . @rpath/SDL2_image.framework/Versions/A/SDL2_image @executable_path/../../../../Contents/Frameworks/SDL2_image.framework/Versions/A/SDL2_image
osxrelocator -r . @rpath/SDL2_mixer.framework/Versions/A/SDL2_mixer @executable_path/../../../../Contents/Frameworks/SDL2_mixer.framework/Versions/A/SDL2_mixer
popd

echo "-- Deactivate virtualenv, is time to relocate things"
deactivate

echo "-- Relocate virtualenv"
pushd "$APP_NAME.app/Contents/Resources/venv/bin"
rm python
ln -s ../../python3/bin/python3 python
sed -E -i '.bak' 's#^VIRTUAL_ENV=.*#VIRTUAL_ENV=$(cd $(dirname "$BASH_SOURCE"); dirname `pwd`)#' activate
popd

echo "-- Copy kivy_activate to ${APP_NAME}.app/Contents/Resources/venv/bin"
cp "${SCRIPT_PATH}/data/kivy_activate" "${APP_NAME}.app/Contents/Resources/venv/bin"

echo "-- Let's fix Frameworks signing."
codesign -fs - "${APP_NAME}.app/Contents/Frameworks/SDL2.framework/Versions/A/SDL2"
codesign -fs - "${APP_NAME}.app/Contents/Frameworks/SDL2_ttf.framework/Versions/A/SDL2_ttf"
codesign -fs - "${APP_NAME}.app/Contents/Frameworks/SDL2_image.framework/Versions/A/SDL2_image"
codesign -fs - "${APP_NAME}.app/Contents/Frameworks/SDL2_mixer.framework/Versions/A/SDL2_mixer"

echo "-- Launch relocate.sh to relocate deps"
../relocate.sh "$APP_NAME.app"

popd

echo "-- Done !"
