# Cleanup script for cleaning up <yourapp>.app
#
#

if [ 'x$1' == 'x' ]; then
    echo "Usage: cleanup_app.py <app_name.app>"
    exit 1
fi

APPPATH=$1

PYPATH="$APPPATH/Contents/Frameworks/python"
rm -rf "$APPPATH/"Contents/Resources/kivy/{doc,build,examples}
rm -rf "$APPPATH/"Contents/Resources/kivy/kivy/{tools,tests}
rm -rf "$APPPATH/"Contents/Resources/venv/bin/{cython*,cygdb,osxrelocator,pip*,pygmentize,easy_install*,rst*}
rm -rf "$APPPATH/"Contents/Resources/venv/lib/python3.*/site-packages/{pip*,Cython*,setuptools*,osxrelocator*,cython*,wheel/test*}
rm -rf "$APPPATH/"Contents/Resources/venv/lib/python3.*/site-packages/wheel/test
rm -rf "$PYPATH/"3.*/lib/python3.*/{turtledemo,test,curses,unittest,ensurepip,idlelib,pydoc_data,setuptools*}
rm -rf "$PYPATH/"3.*/lib/python3.*/site-packages/{easy_install*,pip*}
rm -rf "$PYPATH/"3.*/lib/python3.*/site-packages/wheel/test
rm -rf "$PYPATH/3.*/lib/python3.*/sqlite3"
rm -rf "$PYPATH/3.*/lib/python3.*/tkinter"
rm -rf "$PYPATH/"3.*/bin/{pygmentize,2to*,pip*,*-config,easy_install*,idle*,pydoc*,python3.5m*,rst*,pip*}
rm -rf "$PYPATH/"3.*/lib/{lib*,pkgconfig}
rm -rf "$PYPATH/"3.*/include
rm -rf "$PYPATH/3.*/lib/pkgconfig"
