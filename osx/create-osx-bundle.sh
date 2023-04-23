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
PYVER="3.11.2"
OPENSSL_VERSION="1.1.1t"
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
BUILD_FOLDER=$(pwd)/build
pushd $BUILD_FOLDER

echo "-- Download needed files"
curl -L -O "http://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz"
curl -L -O "https://www.python.org/ftp/python/${PYVER}/Python-${PYVER}.tgz"

echo "-- Copy the Kivy dependencies build script, or download it (from master) if not available"
if [ -f "$KIVY_PATH/tools/build_macos_dependencies.sh" ]; then
    cp "$KIVY_PATH/tools/build_macos_dependencies.sh" .
else
    curl -L -O "https://raw.githubusercontent.com/kivy/kivy/master/tools/build_macos_dependencies.sh"
fi

echo "-- Set MACOSX_DEPLOYMENT_TARGET=10.13"
export SDKROOT=$(xcrun -sdk macosx --show-sdk-path)
export MACOSX_DEPLOYMENT_TARGET=10.13

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
PKG_CONFIG="" ./configure --prefix=$KIVY_APP_PYTHON_PREFIX --enable-universalsdk --disable-test-modules --with-universal-archs=universal2 --with-openssl=../openssl
make
make install
popd

echo "-- Build Kivy dependencies via build_macos_dependencies.sh"
chmod +x build_macos_dependencies.sh
./build_macos_dependencies.sh

echo "-- Create a virtualenv in ${APP_NAME}.app/Contents/Resources"
pushd "$APP_NAME.app/Contents/Resources/"
$KIVY_APP_PYTHON_BIN -m pip install --upgrade pip virtualenv --user
$KIVY_APP_PYTHON_BIN -m venv venv

echo "-- Activate the just created virtualenv"
source venv/bin/activate
popd

echo "-- Ensure KIVY_DEPS_ROOT is set to the dependencies folder"
export KIVY_DEPS_ROOT=$(pwd)/kivy-dependencies

echo "-- Write (or load, and add Kivy) the requirements.in file"
if [ -d "$KIVY_PATH" ]; then
    KIVY_REQ_LINE="${KIVY_PATH}[${EXTRAS}]"
else
    KIVY_REQ_LINE="kivy[${EXTRAS}] @ $KIVY_PATH"
fi
echo $KIVY_REQ_LINE > kivy-app-requirements.in

echo "-- Compile the requirements.txt file via pip-compile, so we have a full list of dependencies"
# This step is needed as the --platform option during pip install requires --no-deps
pip install pip-tools
pip-compile kivy-app-requirements.in --no-annotate --no-header -o kivy-app-requirements.txt

echo "-- Install the requirements via pip"


# This will install macosx_10_9_universal2 and none wheels from PyPI, if available.
# If not, it will install the source distribution and try to build it locally.

SITE_PACKAGES_DIR=$(python -c "import site; print(site.getsitepackages()[0])")

# check if pillow is in kivy-app-requirements.txt file, if so, install it
if grep -q "pillow" kivy-app-requirements.txt; then
    echo "-- Install Pillow via pip (needs to be done separately as it requires specific --global-option flags) and additional dependencies"

    pushd $BUILD_FOLDER

    echo "-- Download needed dependencies (libjpeg, zlib)"
    curl -L -O "http://www.ijg.org/files/jpegsrc.v9d.tar.gz"
    curl -L -O "https://zlib.net/zlib-1.2.13.tar.gz"

    echo "-- Build libjpeg (universal2)"
    tar -xvf "jpegsrc.v9d.tar.gz"
    pushd jpeg-9d
    CFLAGS="-arch x86_64 -arch arm64" ./configure --enable-shared=no --enable-static=yes --prefix=$BUILD_FOLDER/jpeg-9d/build
    make clean
    make install
    popd

    echo "-- Build zlib (universal2)"
    tar -xvf "zlib-1.2.13.tar.gz"
    pushd zlib-1.2.13
    CFLAGS="-arch x86_64 -arch arm64" ./configure  --prefix=$BUILD_FOLDER/zlib-1.2.13/build --static
    make clean
    make install
    popd

    popd

    echo "-- Build Pillow (universal2)"
    CFLAGS="-I$BUILD_FOLDER/jpeg-9d/build/include -I$BUILD_FOLDER/zlib-1.2.13/build/include" \
    LDFLAGS="-L$BUILD_FOLDER/jpeg-9d/build/lib -L$BUILD_FOLDER/zlib-1.2.13/build/lib" \
    PKG_CONFIG="" \
    pip install --platform macosx_10_9_universal2 --no-deps --target $SITE_PACKAGES_DIR Pillow --global-option="build_ext" --global-option="--disable-platform-guessing"

    echo "-- Remove Pillow from kivy-app-requirements.txt file"
    sed -i '' '/pillow/d' kivy-app-requirements.txt
fi

pip install --platform macosx_10_9_universal2 --no-deps --target $SITE_PACKAGES_DIR -r kivy-app-requirements.txt

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
rm python3
rm python
ln -s ../../python3/bin/python3 python3
ln -s python3 python
sed -E -i '.bak' 's#^VIRTUAL_ENV=.*#VIRTUAL_ENV=$(cd $(dirname "$BASH_SOURCE"); dirname `pwd`)#' activate
popd

echo "-- Copy kivy_activate to ${APP_NAME}.app/Contents/Resources/venv/bin"
cp "${SCRIPT_PATH}/data/kivy_activate" "${APP_NAME}.app/Contents/Resources/venv/bin"


echo "-- Copy Kivy dependencies into $APP_NAME.app/Contents/Frameworks directory"
cp -R "$KIVY_DEPS_ROOT/dist/frameworks/." "$APP_NAME.app/Contents/Frameworks"

echo "-- Let's fix Frameworks signing."
codesign -fs - "${APP_NAME}.app/Contents/Frameworks/SDL2.framework/Versions/A/SDL2"
codesign -fs - "${APP_NAME}.app/Contents/Frameworks/SDL2_ttf.framework/Versions/A/SDL2_ttf"
codesign -fs - "${APP_NAME}.app/Contents/Frameworks/SDL2_image.framework/Versions/A/SDL2_image"
codesign -fs - "${APP_NAME}.app/Contents/Frameworks/SDL2_mixer.framework/Versions/A/SDL2_mixer"

echo "-- Launch relocate.sh to relocate deps"
../relocate.sh "$APP_NAME.app"

popd

echo "-- Done !"
