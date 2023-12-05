Kivy SDK Packager
=================

Kivy Software Development Kit (Kivy SDK) is an installable package of all the 
basic dependencies needed to run [Kivy framework](https://kivy.org) apps.

Installing them as a single package may save time.

The Kivy SDK Packager (kivy-sdk-packager) repository contains
the definitions of the SDK for each of three different platforms, and the tools 
to build and distribute them.

This repository contains scripts for Kivy SDK generation on Windows, macOS and
Linux.

Kivy SDK Packager is managed by the [Kivy Team](https://kivy.org/about.html).

[![Backers on Open Collective](https://opencollective.com/kivy/backers/badge.svg)](#backers)
[![Sponsors on Open Collective](https://opencollective.com/kivy/sponsors/badge.svg)](#sponsors)
[![GitHub contributors](https://img.shields.io/github/contributors-anon/kivy/kivy-sdk-packager)](https://github.com/kivy/kivy-sdk-manager/graphs/contributors)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)

## Linux (Debian)

Kivy SDKs for Linux are distributed as 
[Personal Package Archives](https://launchpad.net/ubuntu/+ppas) (PPA) files.
They are built and hosted by [Launchpad](https://launchpad.net/) to the
specifications (recipes) provided here.

| Version      | SDK Binary                                                                                           | Source                                                                                          |
|--------------|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| Stable Build | [Launchpad PPA packages](https://code.launchpad.net/~kivy-team/+archive/ubuntu/kivy/+packages)       | [Launchpad recipes](https://code.launchpad.net/~kivy-team/+archive/ubuntu/kivy/+packages)       |
| Daily Build  | [Launchpad PPA packages](https://code.launchpad.net/~kivy-team/+archive/ubuntu/kivy-daily/+packages) | [Launchpad recipes](https://code.launchpad.net/~kivy-team/+archive/ubuntu/kivy-daily/+packages) |

[Kivy SDK for Linux README](linux/debian/README.md)

## macOS

Kivy SDKs for macOS are built as Disk Image (DMG) files.

These can be built on the developer's machine. 

> [!NOTE]: 
> A Kivy.app build on one macOS version will typically not work on earlier
> macOS versions. You need to build Kivy SDKs for macOS on the oldest machine 
> you wish to support.

[Buildozer](https://buildozer.readthedocs.io) builds and uses Kivy SDKs to 
package macOS apps.

[![macOS Tests](https://github.com/kivy/kivy-sdk-packager/actions/workflows/test_macos.yaml/badge.svg)](https://github.com/kivy/kivy-sdk-packager/actions/workflows/test_macos.yaml)

[Kivy SDK for macOS README](osx/README.md)

## Windows

Kivy SDK for Windows are built as wheels that can be installed via 
[pip](https://pypi.org/project/pip/). They are uploaded and hosted on the 
[Python Package Index](https://pypi.org/) (PyPI).

Four variants are released, based on four different 
[OpenGL ES](https://en.wikipedia.org/wiki/OpenGL_ES) implementations:

| Version                                                                 | PyPI Name                                                            |
|-------------------------------------------------------------------------|----------------------------------------------------------------------|
| [Angle](https://chromium.googlesource.com/angle/angle/+/main/README.md) | [kivy-deps.angle](https://pypi.org/project/kivy-deps.angle/)         |
| [Glew](https://glew.sourceforge.net/)                                   | [kivy-deps.glew](https://pypi.org/project/kivy-deps.glew/)           |
| [Gstreamer](https://gstreamer.freedesktop.org/)                         | [kivy-deps.gstreamer](https://pypi.org/project/kivy-deps.gstreamer/) |
| [SDL2](https://www.libsdl.org/)                                         | [kivy-deps.sdl2](https://pypi.org/project/kivy-deps.sdl2/)           |



[![Windows Angle wheels](https://github.com/kivy/kivy-sdk-packager/actions/workflows/windows_angle_wheels.yml/badge.svg)](https://github.com/kivy/kivy-sdk-packager/actions/workflows/windows_angle_wheels.yml)
[![Windows Glew wheels](https://github.com/kivy/kivy-sdk-packager/actions/workflows/windows_glew_wheels.yml/badge.svg)](https://github.com/kivy/kivy-sdk-packager/actions/workflows/windows_glew_wheels.yml)
[![Windows Gstreamer wheels](https://github.com/kivy/kivy-sdk-packager/actions/workflows/windows_gstreamer_wheels.yml/badge.svg)](https://github.com/kivy/kivy-sdk-packager/actions/workflows/windows_gstreamer_wheels.yml)
[![Windows SDL2 wheels](https://github.com/kivy/kivy-sdk-packager/actions/workflows/windows_sdl2_wheels.yml/badge.svg)](https://github.com/kivy/kivy-sdk-packager/actions/workflows/windows_sdl2_wheels.yml)

[Kivy SDK for Windows README](win/README.md)

## License

Kivy SDK Packager is [MIT licensed](LICENSE), actively developed by a great
community and is supported by many projects managed by the 
[Kivy Organization](https://www.kivy.org/about.html).

## Support

Are you having trouble using Kivy SDK Packager or any of its related projects in the Kivy
ecosystem?
Is there an error you don’t understand? Are you trying to figure out how to use 
it? We have volunteers who can help!

The best channels to contact us for support are listed in the latest 
[Contact Us](https://github.com/kivy/kivy-sdk-packager/blob/master/CONTACT.md) document.

## Contributing

Kivy SDK Packager is part of the [Kivy](https://kivy.org) ecosystem - a large group of
products used by many thousands of developers for free, but it
is built entirely by the contributions of volunteers. We welcome (and rely on) 
users who want to give back to the community by contributing to the project.

Contributions can come in many forms. See the latest 
[Contribution Guidelines](https://github.com/kivy/kivy-sdk-packager/blob/master/CONTRIBUTING.md)
for how you can help us.

## Code of Conduct

In the interest of fostering an open and welcoming community, we as 
contributors and maintainers need to ensure participation in our project and 
our sister projects is a harassment-free and positive experience for everyone. 
It is vital that all interaction is conducted in a manner conveying respect, 
open-mindedness and gratitude.

Please consult the [latest Code of Conduct](https://github.com/kivy/kivy-sdk-packager/blob/master/CODE_OF_CONDUCT.md).

## Contributors

This project exists thanks to 
[all the people who contribute](https://github.com/kivy/kivy-sdk-packager/graphs/contributors).
[[Become a contributor](CONTRIBUTING.md)].

<img src="https://contrib.nn.ci/api?repo=kivy/kivy-sdk-packager&pages=5&no_bot=true&radius=22&cols=18">

## Backers

Thank you to [all of our backers](https://opencollective.com/kivy)! 
🙏 [[Become a backer](https://opencollective.com/kivy#backer)]

<img src="https://opencollective.com/kivy/backers.svg?width=890&avatarHeight=44&button=false">

## Sponsors

Special thanks to 
[all of our sponsors, past and present](https://opencollective.com/kivy).
Support this project by 
[[becoming a sponsor](https://opencollective.com/kivy#sponsor)].

Here are our top current sponsors. Please click through to see their websites,
and support them as they support us. 

<!--- See https://github.com/orgs/kivy/discussions/15 for explanation of this code. -->
<a href="https://opencollective.com/kivy/sponsor/0/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/0/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/1/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/1/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/2/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/2/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/3/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/3/avatar.svg"></a>

<a href="https://opencollective.com/kivy/sponsor/4/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/4/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/5/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/5/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/6/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/6/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/7/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/7/avatar.svg"></a>

<a href="https://opencollective.com/kivy/sponsor/8/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/8/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/9/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/9/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/10/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/10/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/11/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/11/avatar.svg"></a>

<a href="https://opencollective.com/kivy/sponsor/12/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/12/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/13/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/13/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/14/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/14/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/15/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/15/avatar.svg"></a>
