Windows
=======

Pull request CI
---------------

The five Windows dependency workflows run on pull requests whose changed files
match each workflow's path filters. Each PR filter mirrors that workflow's push
filter. Builds and Kivy integration tests report their actual results, including
failures. Server and PyPI publication requires a publish marker in the push
event's head commit message, so publication is skipped on pull request events.

Kivy integration targets
------------------------

Dependency wheels are built first, then checked against selected Kivy test targets:

| Dependency | Python | Kivy ref | GL backend |
| --- | --- | --- | --- |
| ANGLE (forward-compatibility smoke) | 3.9–3.10 | `2.3.1` | `angle_sdl2` |
| GLEW / GStreamer | 3.9–3.10 | `2.3.1` | `angle_sdl2` |
| ANGLE / GLEW / GStreamer | 3.11–3.14 | `master` | `angle_sdl3` |
| SDL2 | 3.9–3.13 | `2.3.1` | `angle_sdl2` |
| SDL3 | 3.11–3.14 | `master` | `angle_sdl3` |

This gives 27 x64 build/integration combinations: 11 stable and 16 development.
Stable and development name the test profiles; two stable ANGLE rows are
forward-compatibility smoke tests.

The older ANGLE rows lift Kivy 2.3.1's `kivy_deps.angle~=0.4.0`
pin to exercise ANGLE 0.5.0.
Normal Kivy 2.3.1 installations resolve ANGLE 0.4.x; these checks do not
establish a supported released installation with ANGLE 0.5.0.

`Test-kivy -KivyTestTarget stable` selects released Kivy 2.3.1 and the
pytest 8.3.5 / pytest-asyncio 0.24.0 pins in
[`ci/kivy-stable-test-constraints.txt`](../ci/kivy-stable-test-constraints.txt).
`Test-kivy -KivyTestTarget development` selects current master. The helper logs
the actual source commit, backend, Kivy version, and runner versions.

Integration explicitly reinstalls the locally built runtime/development wheel
pair. Their file URLs and SHA-256 hashes constrain both runtime and isolated
build dependencies using pip >=25.3. Installed wheel origins and archive hashes
are verified before and after a successful suite; the constraints and verification
results are printed in the job log. This checks which wheel archives were installed,
without tracing every native DLL loaded by a provider.

The separate [Windows CI helper tests](../.github/workflows/windows_ci_tests.yml)
workflow runs `ci/tests/test_local_wheels.py` once on relevant PRs/pushes. These
regressions test selection, installed origins, and real pip build isolation using
synthetic wheels. Test-only changes select this workflow without rebuilding native
dependencies. To run them locally from the repository root (Python 3.9+,
pip >=25.3, and PowerShell):

```powershell
python -m unittest discover -s ci/tests -p "test_local_wheels.py" -v
```

The wheel workflows' `Test package` steps run the installed Kivy test suite.

Stable results cover the tests collected from the released 2.3.1 suite.
Its inherited async-app decorator pattern prevents those async app tests from
being collected with this runner. A successful stable job therefore does not
establish async-app coverage. Async-harness repair is a separate follow-up;
see the [later upstream pytest/async-harness repair](https://github.com/kivy/kivy/commit/122596b656304aef81b53de2aebfc53bd24f0ecc)
for background.

The table describes the selected test coverage: common-dependency rows
on Python 3.11–3.14 exercise development Kivy. SDL2's rows exercise stable Kivy.
Future SDL3 wheel rows start at Python 3.11; previously published artifacts
remain available.

Windows jobs have a 30-minute timeout, except ANGLE's native dependency
preparation, which has a three-hour timeout. A full x86/x64 ANGLE build can
take over two hours. These limits apply separately to each job.

Process to make a new release
-----------------------------

* For each dependency, 
  * go through and check if there has been a new release, if so, update the version to the most recent version.
    * If there's no explicit release, such as for ``angle`` where we use latest master, check the dates to see if there has been new commits since the last release to determine if we need a new release.
  * Check that the download url is still valid.
    * If there are multiple files downloaded per dependency make sure they are all valid.
  * Increment ``__version__`` so a new package will be available for pypi.
* The Windows GitHub CI runs for the specific deps whose path filters match on pull requests and on pushes to the `master` and `windows_ci` branches. Test changes in a pull request; pushing to `windows_ci` remains available for branch-based testing. Sometimes it's expected that the test will fail, e.g. a new python version doesn't have all the other deps on pypi yet.
* When things work, push to master with `[publish xxx win]`, where `xxx` is e.g. `gstreamer`. Then it will also upload the new wheels to the server and pypi. Even if it fails the tests or to upload, it should still show as a build artifact to be manually uploaded to pypi and the server. `[publish xxx win]` must be listed once for each dependency in the commit message.
