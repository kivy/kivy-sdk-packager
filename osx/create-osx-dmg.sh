#!/bin/bash
set -x  # verbose
set -e  # exit on error

USAGE="Creates a dmg from a bundle previously created with create-osx-bundle.sh.

Usage: create-osx-dmg.sh <Path to bundle.app> <App name> [options]

    -s --symlink     <Include symlink script, default:0>          \
Whether to include the symlink creation button for creating a kivy binary under /usr/local/bin. One of 0 or 1.
    -b --background     <Background image, default:data/background.png>          \
The path to the background image when installing the DMG.

Requirements::

    A previously created bundle using create-osx-bundle.sh

For Example::

    ./create-osx-dmg.sh MyApp.app MyApp -s 1
"

if [ $# -lt 2 ]; then
    echo "$USAGE"
    exit 1
fi

BUNDLE_PATH="$1"
APP_NAME="$2"
shift
shift

COPY_SYMLINK="0"
DMG_BACKGROUND_IMG="data/background.png"
while [[ "$#" -gt 0 ]]; do
    # empty arg?
    if [ -z "$2" ]; then
        echo "$USAGE"
        exit 1
    fi

    case $1 in
        -s|--symlink) COPY_SYMLINK="$2";;
        -b|--background) DMG_BACKGROUND_IMG="$2";;
        *) echo "Unknown parameter passed: $1"; echo "$USAGE"; exit 1 ;;
    esac
    shift; shift
done

SYMLINKS_SCRIPT="MakeSymlinks"
VOL_NAME="${APP_NAME}"
DMG_TEMP="${VOL_NAME}-temp.dmg"
DMG="${VOL_NAME}.dmg"
STAGING_DIR="_install"

work_dir="$(mktemp -d -t kivy_app)"
rm "$DMG" || true

echo "-- Copy application into install dir"
mkdir "$work_dir/${STAGING_DIR}"
cp -a "$BUNDLE_PATH" "$work_dir/${STAGING_DIR}"
ln -s /Applications "$work_dir/${STAGING_DIR}/Applications"
mkdir "$work_dir/${STAGING_DIR}/.background"
cp "$DMG_BACKGROUND_IMG" "$work_dir/${STAGING_DIR}/.background/"

if [ "$COPY_SYMLINK" != "0" ]; then
    cp "data/${SYMLINKS_SCRIPT}" "$work_dir/${STAGING_DIR}/${SYMLINKS_SCRIPT}"
fi

# create the initial dmg
echo "-- Create volume"
du -sm "$work_dir/${STAGING_DIR}" | awk '{print $1}' > "$work_dir/_size"
expr "$(cat "$work_dir/_size")" + 99 > "$work_dir/_size"

hdiutil create -srcfolder "$work_dir/${STAGING_DIR}" -volname "${VOL_NAME}" -fs HFS+ \
	-format UDRW -size "$(cat "$work_dir/_size")M" \
	"$work_dir/${DMG_TEMP}"
	#-fsargs "-c c=64,a=16,e=16"
rm "$work_dir/_size"

# mount possible previous dmg
hdiutil unmount "/Volumes/${VOL_NAME}" || true

# mount the dmg
DEVICE=$(hdiutil attach -readwrite -noverify "$work_dir/${DMG_TEMP}" | \
         egrep '^/dev/' | sed 1q | awk '{print $1}')
sleep 2

# tell the Finder to resize the window, set the background,
#  change the icon size, place the icons in the right position, etc.
echo '
   tell application "Finder"
     tell disk "'"$VOL_NAME"'"
           open
           set current view of container window to icon view
           set toolbar visible of container window to false
           set statusbar visible of container window to false
           delay 1
		   set the bounds of container window to {100, 100, 650, 501}
           delay 1
           set viewOptions to the icon view options of container window
           set arrangement of viewOptions to not arranged
           set icon size of viewOptions to 128
           set background picture of viewOptions to file ".background:'"$(basename "$DMG_BACKGROUND_IMG")"'"
           set position of item "'"$APP_NAME.app"'" of container window to {160, 265}
           set position of item "Applications" of container window to {384, 265}
           close
           open
           update without registering applications
           delay 2
     end tell
   end tell
' | osascript

echo "Osascript Finished"
sync
sleep 10

# unmount it
hdiutil detach "${DEVICE}"

# convert to the final format
hdiutil convert "$work_dir/$DMG_TEMP" -format UDZO -imagekey zlib-level=9 -o "$DMG"

# clean
rm -rf "$work_dir"
