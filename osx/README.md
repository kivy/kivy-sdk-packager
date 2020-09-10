Kivy packaging for OS X
=======================

This repository contains the scripts for packaging a Kivy based app into a installable dmg.

Kivy versions supported: ``2.0.0+``. For older Kivy versions, use the corresponding stable branch.

The packaged dmg contains a Python virtualenv, Kivy and its binary dependencies such as SDL2. Kivy 
provides an existing dmg containing the virtualenv and Kivy pre-installed that can be used
as a base into which your app can be installed and packaged again as a dmg. Below are the steps:

* Get the Kivy sdk repo with e.g.
  ``git clone https://github.com/kivy/kivy-sdk-packager.git`` and ``cd`` into
  ``kivy-sdk-packager/osx``.
* Make or download a app bundle:
  * To make a app bundle, simply run::

        ./create-osx-bundle.sh -n MyApp -k ...

    See in ``create-osx-bundle.sh`` for all the configuration options. This will create
    a ``MyApp.app`` directory, where ``MyApp`` is the app's name.
  * To use the existing Kivy app bundle:
    * Download the Kivy app from the Kivy download page, the GitHub releases, or the
      nightly release with e.g.::

          curl -O -L https://xxx/Kivy-2.0.0-python3.8.dmg
    * Mount it in the current directory and fix the name to your App's name::

          hdiutil attach Kivy-2.0.0-python3.8.dmg -mountroot .
          mv Kivy/Kivy.app MyApp.app

      This should create the ``MyApp.app`` directory.
    * Fix the app's metadata to your app's metadata::

          ./fix-bundle-metadata.sh MyApp.app -n MyApp ...
* Install your dependencies and your app:
  * Activate the included virtualenv so you can install your app and its dependencies::

      pushd MyApp.app/Contents/Resources/venv/bin
      source activate
      popd

    On the default mac shell you must be in the bin directory to be able to activate the virtualenv.
  * Install any frameworks and relocate them:
    * Mount any frameworks e.g. ``MyFramework`` on your system and copy it over to the app::

        hdiutil attach MyFramework.dmg
        cp -a /Volumes/MyFramework/MyFramework.framework MyApp.app/Contents/Frameworks/

    * Relocate the framework so it can be used from a different path. E.g.::

        python -m pip install git+https://github.com/tito/osxrelocator
        osxrelocator -r MyApp.app MyApp.app/Contents/Frameworks/SDL2_ttf/ @executable_path/../Frameworks/MyFramework/
        osxrelocator -r MyApp.app @rpath/MyFramework.framework/Versions/A/MyFramework \
            @executable_path/../Frameworks/MyFramework.framework/Versions/A/MyFramework

      This should be customized for each framework.
  * Install your dependencies with e.g. ``pip``::

      python -m pip install ...
  * Install your app::

      python -m pip install myapp
  * Deactivate the virtualenv by running ``deactivate`` in the shell.
* Reduce app size (optional):

  You can reduce the app size by removing unnecessary files. We provide a script to remove files commonly
  not needed and optionally gstreamer (see its options). Run it with::

      ./cleanup-app.sh MyApp.app

  And/or manually remove files and directories.
* Create a script that will run when the user clicks on the installed app.

  To do this, you'll copy a shell, python file, or other script into
  ``MyApp.app/Contents/Resources`` with the name ``yourapp``. The app will automatically run it.

  A common technique is in your ``setup.py`` add something like::

      entry_points={'console_scripts': ['myapp=myapp.main:run_app']}

  to your ``setup`` function. When you install your app package, pip will create a ``myapp``
  script that runs your app. Then, create a symlink to ``myapp``, and your app will run
  when the user clicks the applications. E.g.::

      ln -s "MyApp.app/Contents/Resources/venv/bin/myapp" MyApp.app/Contents/Resources/yourapp

  will create such a symlink.
* Relocate the hard-coded links created by pip. This is required to be able to compile the app
  into a dmg install to a different path. Do::

      ./relocate.sh MyApp.app
* Finally, package the app into a dmg as follows::

      ./create-osx-dmg.sh MyApp.app MyApp

  This creates the MyApp.dmg in your current directory.
* Clean up and unmount and mounted DMGs if needed.


Buildozer uses this repository for its OS X packaging process.
