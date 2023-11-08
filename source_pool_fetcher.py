#!/usr/bin/env python3
"""
Source pool fetcher

Provides methods for generating pools of source files

.. versionadded:: {{NEXT_RELEASE}}
"""

from utils.repos import RepoHelper
from pathlib import Path
from io import BytesIO
import requests
import rpmfile
import shutil

class BaseSourceFetcher:
    """
    Base class for implementing source fetchers.
    Derived classes should inherit from it.
    """

    version_filename = ".version_id"
    def __init__(self, target_dir):
        self.target_dir = Path(target_dir)

        # create the target dir if it doesn't exist
        self.target_dir.mkdir(exist_ok=True)

    def fetch_sources(self):
        """
        Fetch new versions of sources to store locally.
        """
        raise NotImplementedError()

    def ensure_package(self, collection, package, remove_contents=False):
        """
        Ensures the package directory exists, if not, creates it.
        :param collection: The collection
        :param package: the package
        :param remove_contents: clean up the package directory (useful for refreshing)
        :return: A `Path` object to the directory
        """
        collection_dir = self.target_dir / collection
        package_dir = collection_dir / package

        # cleanup if needed
        if remove_contents and package_dir.exists():
            shutil.rmtree(package_dir)

        collection_dir.mkdir(exist_ok=True)
        package_dir.mkdir(exist_ok=True)
        return package_dir

    def write_package_version(self, collection, package, version_id):
        """
        Writes the package version information in a standard way
        :param collection: The collection name
        :param package: the package name
        :param version_id: the unique identifier (url, disturl, version info, etc)
        """
        package_dir = self.ensure_package(collection, package)
        with open(package_dir / self.version_filename, "w") as version_file:
            version_file.write(version_id)

    def check_package(self, collection, package, version_id):
        """
        Check if a package is up-to-date or not. If the package doesn't exist, a directory for it
        gets created

        :param collection: The name of the collection (in the openSUSE example would be `leap-15.6`,
                           `tumbleweed`, etc
        :param package: The name of the package itself
        :param version_id: Something that identifies the package contents and. Could be a version
                           string, a URL to the package rpm file, a disturl, etc
        :return: True if the package is up-to-date, False otherwise
        """
        package_dir = self.ensure_package(collection, package)
        version_file_path = package_dir / self.version_filename

        if not version_file_path.exists():
            return False

        with open(version_file_path, "r") as version_file:
            version = version_file.read()
            return version == version_id


class OpenSuseSourceFetcher(BaseSourceFetcher):
    """
    Fetches openSUSE source rpms and stores them unpacked in
    """

    distro_paths = {
        "tumbleweed": "https://download.opensuse.org/source/tumbleweed/repo/oss/",
        "leap-15.6": "https://download.opensuse.org/source/distribution/leap/15.6/repo/oss/",
        "leap-15.5": "https://download.opensuse.org/source/distribution/leap/15.5/repo/oss/",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.sessions.Session()

    def download_rpm(self, rpm_url):
        """
        Downloads a rpm file and instatiates a handler for it

        :param rpm_url: The url to the rpm file
        :return: `rpmfile.RPMFile` object
        """
        package = self.session.get(rpm_url).content
        return rpmfile.open(fileobj=BytesIO(package))

    def fetch_sources(self):
        """
        Fetch source rpm packages and unpack them in the target directory
        """
        repo_helper = RepoHelper(session = self.session)
        package_collection = {distro: list(repo_helper.get_source_packages(base_url))
                              for distro, base_url in self.distro_paths.items()}

        for collection, packages in package_collection.items():
            for package, package_url in packages:
                if not self.check_package(collection, package, package_url):
                    print(f"Package {collection}/{package} is outdated")
                    package_dir = self.ensure_package(collection, package, remove_contents=True)
                    rpm = self.download_rpm(package_url)
                    for member in rpm.getmembers():
                        with open(package_dir / member.name, "wb") as target_file:
                            target_file.write(rpm.extractfile(member).read())
                    # last but not least, write the package identifier
                    self.write_package_version(collection, package, package_url)


if __name__ == '__main__':
    # default to the only implementation for now
    fetcher = OpenSuseSourceFetcher(target_dir="./packages")
    fetcher.fetch_sources()
