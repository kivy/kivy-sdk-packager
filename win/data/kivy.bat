@ECHO off

set KIVY_PORTABLE_ROOT=%~dp0
set PY_VER=
set PYTHON_DIR=Python%PY_VER%
set KIVY_DIR=kivy%PY_VER%
ECHO botstrapping Kivy @ %KIVY_PORTABLE_ROOT% with Python %KIVY_PORTABLE_ROOT%%PYTHON_DIR%


IF DEFINED kivy_paths_initialized (GOTO :runkivy)

ECHO Setting Environment Variables:
ECHO #################################

set GST_REGISTRY=%KIVY_PORTABLE_ROOT%gstreamer\registry.bin
ECHO GST_REGISTRY
ECHO %GST_REGISTRY%
ECHO ---------------

set KIVY_SDL2_PATH=%KIVY_PORTABLE_ROOT%SDL2\lib;%KIVY_PORTABLE_ROOT%SDL2\include\SDL2;%KIVY_PORTABLE_ROOT%SDL2\bin
ECHO KIVY_SDL2_PATH
ECHO %KIVY_SDL2_PATH%
ECHO ---------------

set USE_SDL2=1
ECHO USE_SDL2
ECHO %USE_SDL2%
ECHO ---------------

set GST_PLUGIN_PATH=%KIVY_PORTABLE_ROOT%gstreamer\lib\gstreamer-1.0
ECHO GST_PLUGIN_PATH:
ECHO %GST_PLUGIN_PATH%
ECHO ---------------

set PATH=%KIVY_PORTABLE_ROOT%;%KIVY_PORTABLE_ROOT%%PYTHON_DIR%;%KIVY_PORTABLE_ROOT%tools;%KIVY_PORTABLE_ROOT%%PYTHON_DIR%\Scripts;%KIVY_PORTABLE_ROOT%gstreamer\bin;%KIVY_PORTABLE_ROOT%MinGW\bin;%KIVY_PORTABLE_ROOT%SDL2\bin;%PATH%
ECHO PATH:
ECHO %PATH%
ECHO ----------------------------------

set PKG_CONFIG_PATH=%KIVY_PORTABLE_ROOT%gstreamer\lib\pkgconfig;%PKG_CONFIG_PATH%
set PYTHONPATH=%KIVY_PORTABLE_ROOT%%KIVY_DIR%;%PYTHONPATH%
ECHO PYTHONPATH:
ECHO %PYTHONPATH%
ECHO ----------------------------------

SET kivy_paths_initialized=1
ECHO ##################################


:runkivy

ECHO done bootstraping kivy...have fun!\n
IF (%1)==() GOTO SHELL
ECHO running "python.exe %*" \n
python.exe  %*
IF %errorlevel% NEQ 0 (PAUSE)
GOTO END
:SHELL
ECHO.
ECHO -----------------------------------------------------------------------
ECHO - Running a shell, you can browse kivyexamples and launch apps with: -
ECHO - python app.py -
ECHO -----------------------------------------------------------------------
ECHO.
cmd
:END
