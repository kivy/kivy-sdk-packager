#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Updates the metadata of a bundle created with create-osx-bundle.sh.

Usage::

    fix-bundle-metadata.sh <Path to bundle.app> <App name> <App version> <author> <org> <icon>

Requirements::

    A previously created bundle using create-osx-bundle.sh

For Example::

    ./fix-bundle-metadata.sh MyApp.app MyApp 1.2.3 Me org.myorg.myapp my_icon.png
"

if [ $# -lt 6 ]; then
    echo "$USAGE"
    exit 1
fi

PLIST_PATH="$1/Contents/info.plist"

echo "Setting Bundle display name and Bundle name to $2"
plutil -replace "Bundle display name" -string "$2" "$PLIST_PATH"
plutil -replace "Bundle name" -string "$2" "$PLIST_PATH"

echo "Setting Bundle version to $3"
plutil -replace "Bundle version" -string "$3" "$PLIST_PATH"

echo "Setting NSHumanReadableCopyright to $4"
plutil -replace "NSHumanReadableCopyright" -string "$4" "$PLIST_PATH"

echo "Setting Bundle identifier to $5"
plutil -replace "Bundle identifier" -string "$5" "$PLIST_PATH"

echo "Changing icon to $6"
h=$(sips -g pixelHeight "$6")
w=$(sips -g pixelWidth "$6")
if [ "$h" -ne "$w" ]; then
    echo "The icon width and height should be the same, but they are $w x $h"
    exit 1
fi

if [ "${6##*.}" != "icns" ]; then
    sips -s format icns "$6" --out "$1/Contents/Resources/appIcon.icns"
fi

echo "-- Done !"
