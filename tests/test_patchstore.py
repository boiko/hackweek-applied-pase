from datetime import datetime
import logging
import os
import tempfile
import time
import unittest

from patchstore import PatchStore


class TestPatchStore(unittest.TestCase):

    def setUp(self):
        dbfile, filepath = tempfile.mkstemp(suffix='.db')
        os.close(dbfile)
        self.store = PatchStore(filepath)
        for i in range(1, 10):
            self.assertTrue(
                self.store.add(f'patch{i}.patch', f'contents of patch #{i}',
                               f'https://example.org/patches/patch{i}')
            )

    def tearDown(self):
        dbfile = self.store.dbfile
        del self.store
        os.remove(dbfile)

    def test_update_patch_timestamp(self):
        i = 3
        filename = f'patch{i}.patch'
        patch = next(self.store.search_by_filename(filename))
        timestamp = patch.timestamp
        time.sleep(0.1)
        self.assertTrue(
            self.store.add(filename, f'contents of patch #{i}',
                           f'https://example.org/patches/patch{i}')
        )
        patch = next(self.store.search_by_filename(filename))
        self.assertGreater(datetime.fromisoformat(patch.timestamp),
                           datetime.fromisoformat(timestamp))

    def test_search_patches_by_origin(self):
        patches = list(self.store.search_by_origin('https://example.org/patches/'))
        self.assertEqual(len(patches), 9)
        patches = list(self.store.search_by_origin('origin'))
        self.assertEqual(len(patches), 0)

    def test_search_patches_by_filename(self):
        patches = list(self.store.search_by_filename('patch5.patch'))
        self.assertEqual(len(patches), 1)
        patches = list(self.store.search_by_filename('patch42.patch'))
        self.assertEqual(len(patches), 0)

    def test_search_patches_by_content(self):
        patches = list(self.store.search_by_content('contents of patch #4'))
        self.assertEqual(len(patches), 1)
        patches = list(self.store.search_by_content('unknown content'))
        self.assertEqual(len(patches), 0)

    def test_invalid_parameters(self):
        # empty filename
        with self.assertLogs('root', level=logging.ERROR) as cm:
            self.assertFalse(self.store.add('', 'contents', 'origin'))
        self.assertEqual(
            cm.records.pop().msg,
            'Storing a patch requires a filename to identify the patch'
        )

        # invalid patch file extension
        with self.assertLogs('root', level=logging.ERROR) as cm:
            self.assertFalse(self.store.add('patch.txt', 'contents', 'origin'))
        self.assertEqual(
            cm.records.pop().msg,
            'Filename does not match that of a patch file'
        )

        # empty content
        with self.assertLogs('root', level=logging.ERROR) as cm:
            self.assertFalse(self.store.add('patch.patch', '', 'origin'))
        self.assertEqual(cm.records.pop().msg, 'Empty patch contents')

        # empty origin
        with self.assertLogs('root', level=logging.ERROR) as cm:
            self.assertFalse(self.store.add('patch.patch', 'contents', ''))
        self.assertEqual(cm.records.pop().msg, 'Storing a patch requires a valid origin')

        # invalid timestamps
        with self.assertLogs('root', level=logging.ERROR) as cm:
            self.assertFalse(
                self.store.add('patch.patch', 'contents', 'origin', 'today')
            )
            self.assertFalse(
                self.store.add('patch.patch', 'contents', 'origin', '2023-11-06 11:42:41 UTC')
            )
        self.assertEqual(
            cm.records.pop(0).msg,
            'Invalid timestamp format: today (expects ISO 8601)'
        )
        self.assertEqual(
            cm.records.pop().msg,
            'Invalid timestamp format: 2023-11-06 11:42:41 UTC (expects ISO 8601)'
        )

    def test_valid_timestamp(self):
        self.assertTrue(
            self.store.add('patch.patch', 'contents', 'origin',
                           datetime(2023, 11, 6, 15, 42, 6).isoformat())
        )
