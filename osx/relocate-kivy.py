"""Copy ANGLE runtimes, relocate Kivy's native dependencies, and ad-hoc sign them."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

app, dependencies, kivy = (Path(arg).resolve() for arg in sys.argv[1:])
frameworks = app / "Contents/Frameworks"
original_frameworks = dependencies / "dist/Frameworks"


def otool(flag, binary):
    return subprocess.check_output(
        ["otool", "-arch", "all", flag, str(binary)], text=True
    )


def install_ids(binary):
    lines = (line.strip() for line in otool("-D", binary).splitlines())
    return {line for line in lines if line and not line.endswith(":")}


def load_names(output):
    return {
        line.strip().split(" (compatibility version", 1)[0]
        for line in output.splitlines() if " (compatibility version" in line
    }


def rpaths(output):
    return set(re.findall(
        r"cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset \d+\)", output
    ))


def in_tree(name, root):
    return name == str(root) or name.startswith(f"{root}/")


# Only these framework binaries and the two ANGLE dylibs enter the map.
runtimes = []
for framework in sorted(frameworks.glob("*.framework")):
    canonical = framework / framework.stem
    runtimes.append((original_frameworks / framework.name / framework.stem, canonical))

require_angle = (
    (frameworks / "SDL3.framework").is_dir()
    and os.environ.get("USE_LEGACY_OPENGL", "0") == "0"
)
for name in ("libEGL.dylib", "libGLESv2.dylib"):
    original = dependencies / "dist/lib" / name
    if original.is_file():
        bundled = frameworks / name
        shutil.copy2(original, bundled)
        runtimes.append((original, bundled))
    elif require_angle:
        sys.exit(f"Missing required ANGLE runtime: {original}")

relocations = {}
runtime_binaries = set()
for original, canonical in runtimes:
    binary = canonical.resolve(strict=True)
    binary.relative_to(app)  # Never mutate an input through an external symlink.
    runtime_binaries.add(binary)
    for alias in install_ids(binary) | {str(original), str(original.resolve())}:
        relocations[alias] = binary

extensions = {path.resolve(strict=True) for path in kivy.rglob("*.so")}
if not extensions:
    sys.exit(f"No installed Kivy native extensions found in {kivy}")
consumers = sorted(extensions | runtime_binaries)
for consumer in consumers:
    consumer.relative_to(app)
    ids = install_ids(consumer)
    changes = []
    for old in sorted(load_names(otool("-L", consumer)) - ids):
        if old in relocations:
            relative = os.path.relpath(relocations[old], consumer.parent)
            changes += ["-change", old, f"@loader_path/{relative}"]
    for rpath in sorted(rpaths(otool("-l", consumer))):
        if in_tree(rpath, dependencies):
            changes += ["-delete_rpath", rpath]
    if consumer in runtime_binaries:
        changes += ["-id", f"@rpath/{consumer.relative_to(frameworks)}"]
    # Batch edits so removed rpaths can make room for longer load names.
    if changes:
        subprocess.check_call(["install_name_tool", *changes, str(consumer)])

# Sign after all install-name/rpath mutations, including extension modules.
for consumer in consumers:
    subprocess.check_call(["codesign", "--force", "--sign", "-", str(consumer)])
