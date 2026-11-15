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

| Dependency | Python | Test | Kivy ref | GL backend |
| --- | --- | --- | --- | --- |
| ANGLE / GLEW / GStreamer / SDL2 | 3.11–3.14 | Kivy suite | `2.3.2` | `angle_sdl2` |
| SDL3 | 3.11–3.14 | Kivy suite | `master` | `angle_sdl3` |
| All five | 3.15 | wheel smoke test | none | none |

This gives 25 x64 build/test combinations: 16 stable, 4 development, and 5 smoke.
Stable and development name the Kivy test profiles; three stable ANGLE rows are
forward-compatibility tests.

Wheels are built for Python 3.11 and newer. Previously published wheels for
older Python versions remain available, and Kivy's `~=` pins let those
installations keep resolving them.

Stable Kivy 2.3.2 stands in for a Kivy 2.4 test profile until a 2.4 branch
exists. As a result, ANGLE, GLEW and GStreamer are tested only against SDL2-era
Kivy; Kivy `master` (SDL3) is exercised by the SDL3 workflow.

No Kivy release or `master` supports Python 3.15 yet, and no `kivy_deps` wheels
for it are published, so every 3.15 row (`package-test: smoke`) runs
`Test-wheel-smoke` from [`ci/windows_smoke.ps1`](../ci/windows_smoke.ps1)
instead of the Kivy suite. It installs the local wheel pair,
verifies their origins, and runs [`ci/smoke_test_wheels.py`](../ci/smoke_test_wheels.py).
That script loads the dependency's DLLs by name through the directory the runtime
package registers, as Kivy does, and checks the development headers and import
libraries are installed. Per dependency it also:

* ANGLE: initializes the default EGL display.
* GLEW: checks the GLEW version against `win/glew.py`.
* GStreamer: checks the GStreamer version against `win/gstreamer.py` and finds
  the `playbin`, `appsink`, `videoconvert` and `audioconvert` elements.
* SDL2: checks SDL2, SDL2_image, SDL2_mixer and SDL2_ttf versions against
  `win/sdl2.py` and initializes the image and audio formats Kivy requests.
* SDL3: checks SDL3, SDL3_image, SDL3_mixer and SDL3_ttf versions against
  `win/build_sdl3.ps1` and initializes SDL3_mixer and SDL3_ttf.

Switch the 3.15 rows to the Kivy suite once a Kivy version supports Python 3.15
and the other `kivy_deps` it installs have 3.15 wheels.

The ANGLE rows on Python 3.11–3.13 lift Kivy 2.3.2's `kivy_deps.angle~=0.4.0`
pin (used before Python 3.14) to exercise ANGLE 0.5.0.
Normal Kivy 2.3.2 installations on those Python versions resolve ANGLE 0.4.x;
these checks do not establish a supported released installation with ANGLE 0.5.0.
On Python 3.14, Kivy 2.3.2 itself requires ANGLE 0.5.0.

`Test-kivy -KivyTestTarget stable` selects released Kivy 2.3.2 and the
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
workflow runs `ci/tests/test_local_wheels.py` once on relevant PRs/pushes using
Python 3.11, the oldest supported interpreter. These regressions test selection,
installed origins, and real pip build isolation using synthetic wheels. Test-only
changes select this workflow without rebuilding native dependencies. To run them
locally from the repository root (Python 3.11+, pip >=25.3, and PowerShell 7):

```powershell
python -m unittest discover -s ci/tests -p "test_local_wheels.py" -v
```

The wheel workflows' `Test package` steps run the installed Kivy test suite;
`Smoke test package` steps run the wheel smoke test.

Stable results cover the full released 2.3.2 suite, including its async app
tests, which 2.3.1's decorator pattern kept from being collected. Kivy 2.3.2
fixed that collection in [kivy/kivy#9457](https://github.com/kivy/kivy/pull/9457)
and replaced the UrlRequest tests' live httpbin.org requests with local servers in
[kivy/kivy#9452](https://github.com/kivy/kivy/pull/9452), so stable jobs run the
suite without deselections.

Windows jobs have a 30-minute timeout, except ANGLE's native dependency
preparation, which has a three-hour timeout to allow headroom for source
synchronization and native compilation. ANGLE preparation builds x64
DLLs once and shares the `angle_dlls-x64` artifact across every Python
wheel/integration row. The artifact preserves the `Release_x64/` directory
expected by the packaging recipe. These limits apply separately to each job.

Process to make a new release
-----------------------------

* For each dependency, 
  * go through and check if there has been a new release, if so, update the version to the most recent version.
    * If there's no explicit release, such as for ``angle`` where we use latest master, check the dates to see if there has been new commits since the last release to determine if we need a new release.
  * Check that the download url is still valid.
    * If there are multiple files downloaded per dependency make sure they are all valid.
  * Increment ``__version__`` so a new package will be available for pypi.
* The Windows GitHub CI runs for the specific deps whose path filters match on pull requests and on pushes to the `master` and `windows_ci` branches. Test changes in a pull request; pushing to `windows_ci` remains available for branch-based testing. For a new Python version that Kivy or the other deps don't support on PyPI yet, use `package-test: smoke` rows instead of the Kivy suite.
* When things work, push to master with `[publish xxx win]`, where `xxx` is e.g. `gstreamer`. `[publish xxx win]` must be listed once for each dependency in the commit message. The workflow still builds and tests every Python row; a separate `publish` job then runs only if every row passed. It downloads those rows' tested wheel artifacts, without rebuilding, and uploads them to the server and PyPI. If any row fails, nothing is uploaded, and the built wheels remain available as workflow artifacts. A row that is expected to fail therefore blocks publishing until it is fixed, switched to a smoke test, or removed.
* Publishing never replaces files that are already published: PyPI uploads use `twine --skip-existing`, and server uploads set `UPLOAD_IGNORE_EXISTING` so `ci/windows-server-upload.sh` runs `rsync --ignore-existing`. Re-publishing an existing version therefore uploads only the files that are missing, such as a new Python version's wheels. Changing the contents of published wheels needs a ``__version__`` bump.
* Whether PyPI still accepts new wheels for an older release is unconfirmed. GLEW 0.3.1 accepted wheels for Python 3.11 through 3.14 between 2022 and 2025, while SDL2 added Python 3.14 with a version bump (0.8.1). Before adding a new Python version, try one manual upload of a tested wheel to the existing release; if PyPI rejects it, make a patch release with identical contents.
