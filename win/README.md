Windows
=======

Process to make a new release
-----------------------------

* For each dependency, 
  * go through and check if there has been a new release, if so, update the version to the most recent version.
    * If there's no explicit release, such as for ``angle`` where we use latest master, check the dates to see if there has been new commits since the last release to determine if we need a new release.
  * Check that the download url is still valid.
    * If there are multiple files downloaded per dependency make sure they are all valid.
  * Increment ``__version__`` to cause a new build. Otherwise the dependency will be skipped.
* Commit and push to master (or make a PR).
* Merge into master will cause a build on appveyor (https://ci.appveyor.com/project/KivyOrg/kivy-sdk-packager). Check that all the dependencies that needed to be built have been built and uploaded to https://kivy.org/downloads/ci/win/deps/. Otherwise, fix the issue and increment ``__version__`` to cause a new build of that package.
* Finally, download the wheels (not the `*tar.gz` files), test to make sure they work, and upload to pypi:
  * ``twine upload *.whl``
