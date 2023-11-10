import logging

from patchstore import PatchStore


class PatchCrawler(object):

    """
    Base abstract class for patch crawlers.
    """

    def __init__(self, name: str, store: PatchStore):
        self.name = name
        self.store = store
        self.logger = logging.getLogger(name)

    def crawl(self):
        raise NotImplementedError()
