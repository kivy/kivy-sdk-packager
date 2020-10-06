Windows
=======

Process to make a new release
-----------------------------

* For each dependency, 
  * go through and check if there has been a new release, if so, update the version to the most recent version.
    * If there's no explicit release, such as for ``angle`` where we use latest master, check the dates to see if there has been new commits since the last release to determine if we need a new release.
  * Check that the download url is still valid.
    * If there are multiple files downloaded per dependency make sure they are all valid.
  * Increment ``__version__`` so a new package will be available for pypi.
* The Windows GitHub CI only runs for the specific deps whose files changed and for the `master` and `wndows_ci` branches. So add any changes and test by pushing to the `windows_ci` branch to see if the tests pass. Sometimes it's expected that the test will fail, e.g. a new python version doesn't have all the other deps on pypi yet.
* When things work, push to master with `[publish xxx win]`, where `xxx` is e.g. `gstreamer`. Then it will also upload the new wheels to the server and pypi. Even if it fails the tests or to upload, it should still show as a build artifact to be manually uploaded to pypi and the server. `[publish xxx win]` must be listed once for each dependency in the commit message.
