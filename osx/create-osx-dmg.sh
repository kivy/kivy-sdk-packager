#!/bin/bash

set -e

if [ "X$1" == "X" ]; then
	echo "Usage: $(basename $0) Kivy.app"
	exit 1
fi

set -x

APP_NAME="$(basename $1 .app)"
DMG_BACKGROUND_IMG="background.png"
SYMLINKS_SCRIPT="MakeSymlinks"
VOL_NAME="${APP_NAME}"
DMG_TEMP="${VOL_NAME}-temp.dmg"
DMG="${VOL_NAME}.dmg"
STAGING_DIR="_install"

rm -rf "${STAGING_DIR}" "${DMG}" "${DMG_TEMP}"

echo "-- Copy application into install dir"
mkdir "${STAGING_DIR}"
cp -a $1 "${STAGING_DIR}"
ln -s /Applications "${STAGING_DIR}/Applications"
mkdir "${STAGING_DIR}/.background"
cp "data/${DMG_BACKGROUND_IMG}" "${STAGING_DIR}/.background/"
cp "data/${SYMLINKS_SCRIPT}" "${STAGING_DIR}/${SYMLINKS_SCRIPT}"

# create the initial dmg
echo "-- Create volume"
du -sm "${STAGING_DIR}" | awk '{print $1}' > _size
expr $(cat _size) + 99 > _size
hdiutil create -srcfolder "${STAGING_DIR}" -volname "${VOL_NAME}" -fs HFS+ \
	-format UDRW -size $(cat _size)M \
	"${DMG_TEMP}"
	#-fsargs "-c c=64,a=16,e=16"
rm _size

# mount possible previous dmg
hdiutil unmount "/Volumes/${VOL_NAME}" || true

# mount the dmg
DEVICE=$(hdiutil attach -readwrite -noverify "${DMG_TEMP}" | \
         egrep '^/dev/' | sed 1q | awk '{print $1}')
sleep 2

# tell the Finder to resize the window, set the background,
#  change the icon size, place the icons in the right position, etc.
echo '
   tell application "Finder"
     tell disk "'${VOL_NAME}'"
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
           set background picture of viewOptions to file ".background:'${DMG_BACKGROUND_IMG}'"
           set position of item "'${APP_NAME}'.app" of container window to {160, 265}
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
hdiutil convert "$DMG_TEMP" -format UDZO -imagekey zlib-level=9 -o "$DMG"

# clean
rm -rf "$DMG_TEMP" "$STAGING_DIR"

