import unittest
from unittest.mock import patch

from patchcrawler import PatchCrawler


class TestPatchCrawler(unittest.TestCase):

    def test_init(self):
        with patch('patchstore.PatchStore') as MockStore:
            mockStore = MockStore.return_value
            crawler = PatchCrawler('a crawler', mockStore)
            self.assertEqual(crawler.name, 'a crawler')
            self.assertEqual(crawler.store, mockStore)
            self.assertEqual(crawler.logger.name, 'a crawler')

    def test_crawl_not_implemented(self):
        with patch('patchstore.PatchStore') as MockStore:
            crawler = PatchCrawler('a crawler', MockStore.return_value)
            self.assertRaises(NotImplementedError, crawler.crawl)
