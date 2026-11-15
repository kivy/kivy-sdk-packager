"""Smoke-test installed kivy_deps wheels on Pythons with no Kivy test target.

Run from the repository root with ``PYTHONPATH=.`` (as the wheel workflows set),
after installing the local runtime/development wheel pair (``Test-wheel-smoke``
in ``windows_smoke.ps1`` does both):
    python ci/smoke_test_wheels.py sdl2

DLLs are loaded by name only, so they must resolve through the directories the
runtime package registers on import, as they do for Kivy. Library versions are
compared with the packaging recipe, and the codecs Kivy requests are initialized.
"""

import argparse
import ctypes
import importlib
from pathlib import Path
import re
import sysconfig

ROOT = Path(__file__).resolve().parents[1]


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


def smoke_test_angle():
    ctypes.CDLL('d3dcompiler_47')
    ctypes.CDLL('libGLESv2')
    egl = ctypes.CDLL('libEGL')
    egl.eglGetDisplay.restype = ctypes.c_void_p
    egl.eglGetDisplay.argtypes = [ctypes.c_void_p]
    egl.eglInitialize.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int32),
                                  ctypes.POINTER(ctypes.c_int32)]
    egl.eglQueryString.restype = ctypes.c_char_p
    egl.eglQueryString.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    egl.eglTerminate.argtypes = [ctypes.c_void_p]

    display = egl.eglGetDisplay(None)  # EGL_DEFAULT_DISPLAY
    major, minor = ctypes.c_int32(), ctypes.c_int32()
    if not display or not egl.eglInitialize(display, ctypes.byref(major), ctypes.byref(minor)):
        raise RuntimeError('ANGLE could not initialize the default EGL display')
    print('EGL {}.{} initialized: {}'.format(
        major.value, minor.value, egl.eglQueryString(display, 0x3054).decode()),  # EGL_VERSION
        flush=True)
    egl.eglTerminate(display)


def smoke_test_glew():
    from win import glew as recipe

    glew = ctypes.CDLL('glew32')
    glew.glewGetString.restype = ctypes.c_char_p
    glew.glewGetString.argtypes = [ctypes.c_uint]
    check_version('GLEW', glew.glewGetString(1).decode(), recipe.glew_ver)  # GLEW_VERSION
    check_dev_files('glew', ['include/GL/glew.h', 'include/GL/wglew.h', 'libs/glew32.lib'])


def smoke_test_gstreamer():
    from win import gstreamer as recipe

    # The explicit .dll suffix stops Windows reading ".0-0" as the extension.
    gst = ctypes.CDLL('gstreamer-1.0-0.dll')
    parts = [ctypes.c_uint() for _ in range(4)]
    gst.gst_version(*(ctypes.byref(part) for part in parts))
    check_version('GStreamer', '.'.join(str(part.value) for part in parts[:3]),
                  recipe.gst_ver)

    gst.gst_init(None, None)
    gst.gst_element_factory_find.restype = ctypes.c_void_p
    gst.gst_element_factory_find.argtypes = [ctypes.c_char_p]
    gst.gst_object_unref.argtypes = [ctypes.c_void_p]
    # Elements Kivy's gstplayer pipeline needs, found through GST_PLUGIN_PATH.
    for name in ('playbin', 'appsink', 'videoconvert', 'audioconvert'):
        factory = gst.gst_element_factory_find(name.encode())
        if not factory:
            raise RuntimeError('GStreamer has no {} element'.format(name))
        gst.gst_object_unref(factory)
        print('GStreamer found {}'.format(name), flush=True)

    check_dev_files('gstreamer', ['include/gst/gst.h', 'include/glib.h',
                                  'libs/gstreamer-1.0.lib', 'libs/glib-2.0.lib',
                                  'libs/gobject-2.0.lib'])


def sdl3_version(library, function):
    getter = getattr(library, function)
    getter.restype = ctypes.c_int
    number = getter()
    return '{}.{}.{}'.format(number // 1000000, number // 1000 % 1000, number % 1000)


def smoke_test_sdl3():
    script = (ROOT / 'win' / 'build_sdl3.ps1').read_text()
    versions = dict(re.findall(r'\$WINDOWS__(SDL3\w*?)__VERSION\s*=\s*"([^"]+)"', script))

    sdl = ctypes.CDLL('SDL3')
    check_version('SDL3', sdl3_version(sdl, 'SDL_GetVersion'), versions['SDL3'])
    image = ctypes.CDLL('SDL3_image')
    check_version('SDL3_image', sdl3_version(image, 'IMG_Version'), versions['SDL3_IMAGE'])

    mixer = ctypes.CDLL('SDL3_mixer')
    check_version('SDL3_mixer', sdl3_version(mixer, 'MIX_Version'), versions['SDL3_MIXER'])
    mixer.MIX_Init.restype = ctypes.c_bool
    if not mixer.MIX_Init():
        raise RuntimeError('SDL3_mixer could not initialize')
    mixer.MIX_Quit()

    ttf = ctypes.CDLL('SDL3_ttf')
    check_version('SDL3_ttf', sdl3_version(ttf, 'TTF_Version'), versions['SDL3_TTF'])
    ttf.TTF_Init.restype = ctypes.c_bool
    if not ttf.TTF_Init():
        raise RuntimeError('SDL3_ttf could not initialize')
    ttf.TTF_Quit()

    headers = ['SDL3/SDL.h', 'SDL3_image/SDL_image.h', 'SDL3_mixer/SDL_mixer.h',
               'SDL3_ttf/SDL_ttf.h']
    libs = ['SDL3.lib', 'SDL3_image.lib', 'SDL3_mixer.lib', 'SDL3_ttf.lib']
    check_dev_files('sdl3', ['include/' + name for name in headers] +
                    ['libs/' + name for name in libs])


SMOKE_TESTS = {'angle': smoke_test_angle, 'glew': smoke_test_glew,
               'gstreamer': smoke_test_gstreamer, 'sdl2': smoke_test_sdl2,
               'sdl3': smoke_test_sdl3}


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
