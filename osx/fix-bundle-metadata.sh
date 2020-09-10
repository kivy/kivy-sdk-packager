#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Updates the metadata of a bundle created with create-osx-bundle.sh.

Usage: fix-bundle-metadata.sh <Path to bundle> [options]

    <Path to bundle>    The path to the app bundle (e.g. MyApp.app).

    -n --name     <App name>          The name of the app.
    -v --version  <App version>       The version of the app.
    -a --author   <Author>            The author name.
    -o --org      <org>               The org id used for the app.
    -i --icon     <icon>              A png or icns icon file path.

Requirements::

    A previously created bundle using create-osx-bundle.sh

For Example::

    ./fix-bundle-metadata.sh MyApp.app -n MyNewApp -i my_icon.png
"

if [ $# -lt 1 ]; then
    echo "$USAGE"
    exit 1
fi

APP_PATH="$1"
PLIST_PATH="$1/Contents/info.plist"
shift

while [[ "$#" -gt 0 ]]; do
    # empty arg?
    if [ -z "$2" ]; then
        echo "$USAGE"
        exit 1
    fi

    case $1 in
        -n|--name)
          echo "Setting Bundle display name and Bundle name to $2"
          plutil -replace "Bundle display name" -string "$2" "$PLIST_PATH"
          plutil -replace "Bundle name" -string "$2" "$PLIST_PATH"
          ;;
        -v|--version)
          echo "Setting Bundle version to $2"
          plutil -replace "Bundle version" -string "$2" "$PLIST_PATH"
          ;;
        -a|--author)
          echo "Setting NSHumanReadableCopyright to $2"
          plutil -replace "NSHumanReadableCopyright" -string "$2" "$PLIST_PATH"
          ;;
        -o|--org)
          echo "Setting Bundle identifier to $2"
          plutil -replace "Bundle identifier" -string "$2" "$PLIST_PATH"
          ;;
        -i|--icon)
          echo "Changing icon to $2"
          h=$(sips -g pixelHeight "$2")
          w=$(sips -g pixelWidth "$2")
          if [ "$h" -ne "$w" ]; then
              echo "The icon width and height should be the same, but they are $w x $h"
              exit 1
          fi

          if [ "${2##*.}" != "icns" ]; then
              sips -s format icns "$2" --out "$APP_PATH/Contents/Resources/appIcon.icns"
          else
              cp "$2" "$APP_PATH/Contents/Resources/appIcon.icns"
          fi
          ;;
        *) echo "Unknown parameter passed: $1"; echo "$USAGE"; exit 1 ;;
    esac
    shift; shift
done

echo "-- Done !"
