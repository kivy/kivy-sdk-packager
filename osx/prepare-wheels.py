import argparse
import logging
import os
import tempfile
import urllib.request

from delocate.fuse import fuse_wheels
from distlib.locators import SimpleScrapingLocator
from distlib.wheel import Wheel
from distlib.util import parse_requirement
import packaging.tags
import packaging.version

parser = argparse.ArgumentParser()
parser.add_argument("--requirements-file", help="Path to the requirements file")
parser.add_argument("--python-version", help="Python version", default="3.12")
parser.add_argument(
    "--deployment-target", help="Deployment target", default="11.0"
)
parser.add_argument("--log-level", help="Log level", default="INFO")
parser.add_argument(
    "--output-folder",
    help="The folder where the wheels which have to be installed will be stored",
)
args = parser.parse_args()

logging.basicConfig(level=args.log_level)

deployment_target = packaging.version.parse(args.deployment_target)
deployment_target_tuple = (deployment_target.major, deployment_target.minor)

python_version = packaging.version.parse(args.python_version)
python_version_tuple = (python_version.major, python_version.minor)

mac_platforms = {
    "universal2": list(
        packaging.tags.mac_platforms(
            version=deployment_target_tuple, arch="universal2"
        )
    ),
    "x86_64": list(
        packaging.tags.mac_platforms(
            version=deployment_target_tuple, arch="x86_64"
        )
    ),
    "arm64": list(
        packaging.tags.mac_platforms(
            version=deployment_target_tuple, arch="arm64"
        )
    ),
}

cpython_wheel_tags = {
    "universal2": list(
        packaging.tags.cpython_tags(
            python_version=python_version_tuple,
            platforms=mac_platforms["universal2"],
        )
    ),
    "x86_64": list(
        packaging.tags.cpython_tags(
            python_version=python_version_tuple,
            platforms=mac_platforms["x86_64"],
        )
    ),
    "arm64": list(
        packaging.tags.cpython_tags(
            python_version=python_version_tuple,
            platforms=mac_platforms["arm64"],
        )
    ),
}

compatible_wheel_tags = {
    "universal2": list(
        packaging.tags.compatible_tags(
            python_version=python_version_tuple,
            platforms=mac_platforms["universal2"],
        )
    ),
    "x86_64": list(
        packaging.tags.compatible_tags(
            python_version=python_version_tuple,
            platforms=mac_platforms["x86_64"],
        )
    ),
    "arm64": list(
        packaging.tags.compatible_tags(
            python_version=python_version_tuple,
            platforms=mac_platforms["arm64"],
        )
    ),
}


class WheelLocator(SimpleScrapingLocator):
    def __init__(self, *args, wheel_tags=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloadable_extensions = (".whl",)
        self.wheel_tags = wheel_tags


class SourceLocator(SimpleScrapingLocator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloadable_extensions = self.source_extensions


class Universal2Fuser:
    def __init__(
        self,
        arm64_wheel_path: str,
        x86_64_wheel_path: str,
        universal2_output_dir: str,
    ):
        self.arm64_wheel_path = arm64_wheel_path
        self.x86_64_wheel_path = x86_64_wheel_path
        self.universal2_output_dir = universal2_output_dir

        self.arm64_wheel = Wheel(self.arm64_wheel_path)
        self.x86_64_wheel = Wheel(self.x86_64_wheel_path)

    def _discover_deployment_target(self):
        # The new universal2 wheel need to have the same deployment target as the
        # wheel with the highest deployment target

        # Not implemented yet. For now, just return deployment_target_tuple
        return deployment_target_tuple

    def fuse(self):
        universal2_wheel = Wheel(self.arm64_wheel.filename)
        _first_platform = list(
            packaging.tags.mac_platforms(version=(11, 0), arch="universal2")
        )[0]
        universal2_wheel.arch = [_first_platform]
        fuse_wheels(
            self.arm64_wheel_path,
            self.x86_64_wheel_path,
            os.path.join(self.universal2_output_dir, universal2_wheel.filename),
        )


class DistributionDownloader:
    def __init__(self, distribution_url: str, output_folder: str):
        self.distribution_url = distribution_url
        self.output_folder = output_folder

    def download(self):
        if self.distribution_url.endswith(".whl"):
            wheel = Wheel(self.distribution_url)
            filename = wheel.filename
        else:
            filename = self.distribution_url.split("/")[-1]
        download_path = os.path.join(self.output_folder, filename)
        urllib.request.urlretrieve(self.distribution_url, download_path)
        return download_path


def to_locator_wheel_tag(tag):
    return (tag.interpreter, tag.abi, tag.platform)


locators = {
    "universal2": WheelLocator(
        "https://pypi.org/simple/",
        scheme="legacy",
        wheel_tags=[
            to_locator_wheel_tag(tag)
            for tag in cpython_wheel_tags["universal2"]
            + compatible_wheel_tags["universal2"]
        ],
    ),
    "x86_64": WheelLocator(
        "https://pypi.org/simple/",
        scheme="legacy",
        wheel_tags=[
            to_locator_wheel_tag(tag)
            for tag in cpython_wheel_tags["x86_64"]
            + compatible_wheel_tags["x86_64"]
        ],
    ),
    "arm64": WheelLocator(
        "https://pypi.org/simple/",
        scheme="legacy",
        wheel_tags=[
            to_locator_wheel_tag(tag)
            for tag in cpython_wheel_tags["arm64"]
            + compatible_wheel_tags["arm64"]
        ],
    ),
    "source": SourceLocator("https://pypi.org/simple/", scheme="legacy"),
}

requirements = []

with open(args.requirements_file, encoding="utf-8") as f:
    _requirements_lines = f.read().splitlines()

    for _line in _requirements_lines:
        # Ensure is a valid requirement
        if parse_requirement(_line) is None:
            logging.warning(
                "Invalid requirement line: %s.", _line
            )
            continue
        requirements.append(
            dict(
                description=_line,
                distributions={
                    "universal2": None,
                    "x86_64": None,
                    "arm64": None,
                    "source": None,
                },
            )
        )


for requirement in requirements:
    requirement_description = requirement["description"]
    _distribution = locators["universal2"].locate(requirement_description)

    if _distribution:
        logging.info(
            "Found universal2 or non-platform-specific wheel for %s",
            requirement_description,
        )
        requirement["distributions"]["universal2"] = _distribution
        continue

    # If no universal2-compatible wheel was found, try to find a wheel for the 2 other
    # architectures
    logging.info(
        "No universal or non-platform-specific wheel found for %s",
        requirement_description,
    )

    for arch_name in ["x86_64", "arm64"]:
        _distribution = locators[arch_name].locate(requirement_description)
        if _distribution:
            logging.info(
                "Found %s-compatible wheel for %s",
                arch_name,
                requirement_description,
            )
            requirement["distributions"][arch_name] = _distribution
            continue

        logging.info(
            "No %s-compatible wheel found for %s",
            arch_name,
            requirement_description,
        )

    # If wheels are not found for both x86_64 and arm64, try to find a source distribution
    if not all(
        requirement["distributions"][arch_name]
        for arch_name in ["x86_64", "arm64"]
    ):
        logging.info(
            "No wheel found for %s. Trying to find a source distribution.",
            requirement_description,
        )
        _distribution = locators["source"].locate(requirement_description)
        if _distribution:
            logging.info(
                "Found source distribution for %s", requirement_description
            )
            requirement["distributions"]["source"] = _distribution
            continue

        logging.error(
            "No source distribution found for %s", requirement_description
        )

output_folder = args.output_folder or "wheels"
# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

for requirement in requirements:
    requirement_description = requirement["description"]
    if requirement["distributions"]["universal2"]:
        logging.info(
            "Downloading universal2 or non-platform-specific wheel for %s",
            requirement_description,
        )
        # Download the universal2 or non-platform-specific wheel
        DistributionDownloader(
            requirement["distributions"]["universal2"].download_url,
            output_folder,
        ).download()
        continue

    if all(
        requirement["distributions"][arch_name]
        for arch_name in ["x86_64", "arm64"]
    ):
        # Create a temporary folder to download the wheels for the 2 architectures
        # and then fuse them
        logging.info(
            "Downloading x86_64 and arm64 wheels for %s in tmp folder for fusing",
            requirement_description,
        )
        with tempfile.TemporaryDirectory() as tmp_folder:
            fuse_paths = {}
            for arch_name in ["x86_64", "arm64"]:
                fuse_paths[arch_name] = DistributionDownloader(
                    requirement["distributions"][arch_name].download_url,
                    tmp_folder,
                ).download()

            logging.info(
                "Fusing x86_64 and arm64 wheels for %s", requirement_description
            )
            Universal2Fuser(
                arm64_wheel_path=fuse_paths["arm64"],
                x86_64_wheel_path=fuse_paths["x86_64"],
                universal2_output_dir=output_folder,
            ).fuse()
        continue

    if requirement["distributions"]["source"]:
        logging.info(
            "Downloading source distribution for %s", requirement_description
        )

        DistributionDownloader(
            requirement["distributions"]["source"].download_url,
            output_folder,
        ).download()
        continue
