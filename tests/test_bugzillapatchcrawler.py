from datetime import datetime, timedelta
import logging
import os
import tempfile
import unittest
from unittest.mock import patch

from requests.exceptions import HTTPError

from bugzillapatchcrawler import BugzillaPatchCrawler
from patchstore import PatchStore


class PatchDataMock(object):
    def __init__(self, data):
        self.data = data


class DateTimeMock(object):
    def __init__(self, timestamp):
        self.value = timestamp.isoformat(sep='T', timespec='seconds')


class TestBugzillaPatchCrawler(unittest.TestCase):

    dummy_bz_instance = 'bugzilla.dummy'

    def _instantiate_crawler(self, timestamp: datetime):
        with patch('bugzilla.Bugzilla') as MockBugzilla:
            with patch('bugzilla.bug.Bug') as MockBug:
                patchdata = b'''--- a/main.c
+++ b/main.c
@@ -1,4 +1,4 @@
 int main(int argc, char** argv)
 {
-    return 0;
+    return 1;
 }'''
                bug = MockBug.return_value
                bug.get_attachments.return_value = [
                    {'is_patch': 0},
                    {'is_patch': 1,
                     'last_change_time': DateTimeMock(timestamp - timedelta(hours=1))},
                    {'is_patch': 1,
                     'last_change_time': DateTimeMock(timestamp + timedelta(hours=1)),
                     'file_name': 'fix.patch', 'data': PatchDataMock(patchdata)},
                ]
                bug.weburl = 'https://bugzilla.dummy/bug'
                crawler = BugzillaPatchCrawler(self.store, self.dummy_bz_instance, None, timestamp)
                bz = MockBugzilla.return_value
                bz.query.return_value = [MockBug(crawler.bz, i) for i in range(1, 10)]
                return crawler

    def setUp(self):
        dbfile, filepath = tempfile.mkstemp(suffix='.db')
        os.close(dbfile)
        self.store = PatchStore(filepath)
        self.crawler = self._instantiate_crawler(datetime.now() - timedelta(days=1))

    def tearDown(self):
        del self.crawler
        dbfile = self.store.dbfile
        del self.store
        os.remove(dbfile)

    def test_crawled_recently(self):
        self.crawler = self._instantiate_crawler(datetime.now() - timedelta(minutes=1))
        with self.assertLogs(self.crawler.name, level=logging.INFO) as cm:
            self.crawler.crawl()
        self.assertEqual(
            cm.records.pop().msg,
            'Not an hour has passed since last crawled, not doing anything.'
        )
        self.crawler.bz.query.assert_not_called()

    def test_crawl(self):
        with self.assertLogs(self.crawler.name, level=logging.INFO) as cm:
            self.crawler.crawl()
        self.crawler.bz.query.assert_called_once()
        args = self.crawler.bz.query.call_args.args[0]
        self.assertEqual(args['f1'], 'days_elapsed')
        self.assertEqual(args['o1'], 'lessthaneq')
        self.assertEqual(args['v1'], '2')
        self.assertEqual(args['f2'], 'attachments.ispatch')
        self.assertEqual(args['o2'], 'equals')
        self.assertEqual(args['v2'], '1')
        self.assertTrue(
            self.crawler.store.exists(
                'fix.patch', 'Bugzilla patch crawler', 'https://bugzilla.dummy/bug')
        )
        for message in (
            'Start crawling.',
            'Found 9 bugs with patch attachments that were modified in the last 1 day(s).',
            'Done crawling, added 9 patches.',
        ):
            self.assertEqual(cm.records.pop(0).message, message)

    def test_throttling(self):
        with patch('bugzilla.Bugzilla') as MockBugzilla:
            with patch('bugzilla.bug.Bug') as MockBug:
                bug = MockBug.return_value

                def mock_get_attachments(bug):
                    if bug.counter > 1:
                        return []
                    bug.counter += 1
                    raise HTTPError('429 Client Error: Too Many Requests')

                bug.counter = 0
                bug.get_attachments = lambda: mock_get_attachments(bug)
                self.crawler = BugzillaPatchCrawler(
                    self.store, self.dummy_bz_instance, None, datetime.now() - timedelta(days=1))
                bz = MockBugzilla.return_value
                bz.query.return_value = [MockBug(self.crawler.bz, 42)]
        with self.assertLogs(self.crawler.name, level=logging.INFO) as cm:
            self.crawler.crawl()
        msg = 'Got an HTTP 429 error, throttling requests.'
        self.assertEqual(len([record for record in cm.records if record.message == msg]), 2)
