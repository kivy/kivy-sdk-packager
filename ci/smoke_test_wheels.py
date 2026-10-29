"""Smoke-test installed kivy_deps wheels on Pythons with no Kivy test target.

Run from the repository root with ``PYTHONPATH=.`` (as the wheel workflows set),
after installing the local runtime/development wheel pair (``Test-wheel-smoke``
in ``windows_ci.ps1`` does both):
    python ci/smoke_test_wheels.py sdl2

DLLs are loaded by name only, so they must resolve through the directories the
runtime package registers on import, as they do for Kivy. Library versions are
compared with the packaging recipe, and the codecs Kivy requests are initialized.
"""

import argparse
import ctypes
import importlib
from pathlib import Path
import sysconfig


class SDLVersion(ctypes.Structure):
    _fields_ = [('major', ctypes.c_uint8), ('minor', ctypes.c_uint8),
                ('patch', ctypes.c_uint8)]

    def __str__(self):
        return '{}.{}.{}'.format(self.major, self.minor, self.patch)


def check_version(label, version, expected):
    if str(version) != expected:
        raise RuntimeError('{} version {} does not match the recipe version {}'.format(
            label, version, expected))
    print('{} version: {}'.format(label, version), flush=True)


def check_flags(label, init, flags):
    for name, flag in flags:
        if init(flag) & flag != flag:
            raise RuntimeError('{} could not initialize {}'.format(label, name))
        print('{} initialized {}'.format(label, name), flush=True)


def linked_version(library, function):
    getter = getattr(library, function)
    getter.restype = ctypes.POINTER(SDLVersion)
    return getter().contents


def check_dev_files(target, files):
    data = Path(sysconfig.get_path('data'))
    missing = [path for path in files if not (data / path).is_file()]
    if missing:
        raise RuntimeError('kivy_deps.{}_dev is missing {}'.format(
            target, ', '.join(missing)))
    print('kivy_deps.{}_dev files present under {}'.format(target, data), flush=True)


def smoke_test_sdl2():
    from win import sdl2 as recipe

    sdl = ctypes.CDLL('SDL2')
    version = SDLVersion()
    sdl.SDL_GetVersion(ctypes.byref(version))
    check_version('SDL2', version, recipe.sdl2_ver)

    image = ctypes.CDLL('SDL2_image')
    check_version('SDL2_image', linked_version(image, 'IMG_Linked_Version'),
                  recipe.sdl2_image_ver)
    check_flags('SDL2_image', image.IMG_Init,
                [('JPG', 0x1), ('PNG', 0x2), ('TIF', 0x4), ('WEBP', 0x8)])
    image.IMG_Quit()

    mixer = ctypes.CDLL('SDL2_mixer')
    check_version('SDL2_mixer', linked_version(mixer, 'Mix_Linked_Version'),
                  recipe.sdl2_mixer_ver)
    check_flags('SDL2_mixer', mixer.Mix_Init,
                [('FLAC', 0x1), ('MOD', 0x2), ('MP3', 0x8), ('OGG', 0x10)])
    mixer.Mix_Quit()

    ttf = ctypes.CDLL('SDL2_ttf')
    check_version('SDL2_ttf', linked_version(ttf, 'TTF_Linked_Version'),
                  recipe.sdl2_ttf_ver)
    if ttf.TTF_Init() != 0:
        raise RuntimeError('SDL2_ttf could not initialize')
    ttf.TTF_Quit()

    headers = ['SDL.h', 'SDL_image.h', 'SDL_mixer.h', 'SDL_ttf.h']
    libs = ['SDL2.lib', 'SDL2main.lib', 'SDL2_image.lib', 'SDL2_mixer.lib',
            'SDL2_ttf.lib']
    check_dev_files('sdl2', ['include/SDL2/' + name for name in headers] +
                    ['libs/' + name for name in libs])


SMOKE_TESTS = {'sdl2': smoke_test_sdl2}


def smoke_test(target):
    runtime, dev = (importlib.import_module(name) for name in
                    ('kivy_deps.' + target, 'kivy_deps.{}_dev'.format(target)))
    for module in (runtime, dev):
        print('Imported {} {}'.format(module.__name__, module.__version__), flush=True)
    if not runtime.dep_bins:
        raise RuntimeError('kivy_deps.{} registered no DLL directories'.format(target))
    SMOKE_TESTS[target]()
    print('Smoke test passed: kivy_deps.' + target, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=sorted(SMOKE_TESTS))
    smoke_test(parser.parse_args().target)
