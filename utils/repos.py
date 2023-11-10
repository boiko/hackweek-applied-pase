import requests
import gzip
import logging
import rpm_vercmp
from lxml import objectify
from urllib.parse import urljoin
from collections import namedtuple
from .misc import session_get_with_retries

Package = namedtuple("Package", ("name", "version", "release", "url"))

class RepoHelper:
    def __init__(self, session=None):
        self.session = session or requests.sessions.Session()
        self.logger = logging.getLogger("repo_helper")

    def download_and_unpack(self, url):
        """
        Download the given file and try to unpack it using gzip
        :param url: The full URL to the file to be downloaded/unpacked
        :return:
        """
        self.logger.debug(f"Downloading and unpacking {url}")
        response = session_get_with_retries(self.session, url)
        try:
            data = gzip.decompress(response.content)
        except gzip.BadGzipFile:
            # the best guess is that this is not a gzip file
            data = response.content

        return objectify.fromstring(data)

    def parse_repository_metadata(self, base_url):
        """
        Parses repository metadata from the given UR
        :param base_url: The base url of the repository (without the `repodata` suffix or any file)
        :return: a dict with the metadata type as key and the file full URL as
        """
        metadata = self.download_and_unpack(urljoin(base_url, "repodata/repomd.xml"))
        return {d.get("type"): urljoin(base_url, d.location.get("href")) for d in metadata.data}

    @staticmethod
    def newest_package(first: Package, second: Package):
        """
        Compares the version of the two packages and returns the newest.
        In case they are identical, the first one is returned

        :param first: First package
        :param second: Second package
        :return: the newest of the two
        """
        result = rpm_vercmp.vercmp(f"{first.version}-{first.release}",
                                   f"{second.version}-{second.release}")
        return second if result < 0 else first

    def get_source_packages(self, base_url):
        """
        Extracts from the repository metadata the list of source packages.
        :param base_url: The base URL from which the metadata should be read
        :return: a generator providing tuples of (package, file url) for each package
        """
        # get the list of metadata
        metadata = self.parse_repository_metadata(base_url)

        packages = dict()

        # now get the primary metadata file and parse it
        primary = self.download_and_unpack(metadata["primary"])
        for package in primary.package:
            if package.arch != "src":
                continue
            pkg = Package(str(package.name), package.version.get("ver"), package.version.get("rel"),
                          urljoin(base_url, package.location.get("href")))
            if package.name not in packages:
                packages[package.name] = pkg
            else:
                packages[package.name] = self.newest_package(packages[package.name], pkg)

        return [(pkg.name, pkg.url) for pkg in packages.values()]
