import argparse
from datetime import datetime, timedelta
import logging
import os
import tempfile
import time

from patchcrawler import PatchCrawler
from patchstore import PatchStore

import bugzilla
from requests.exceptions import HTTPError


class BugzillaPatchCrawler(PatchCrawler):

    def __init__(self, store: PatchStore,
                 instance: str, apikey: str, timestamp: datetime):
        """
        :param instance: the Bugzilla instance to target
                         (e.g. https://bugzilla.opensuse.org)
        :param apikey: an optional Bugzilla API key
                       (see https://bugzilla.readthedocs.org/en/5.0/api/core/v1/general.html#authentication)
        :param timestamp: the last time crawler was run
        """
        super().__init__('Bugzilla patch crawler', store)
        self.bz = bugzilla.Bugzilla(instance, api_key=apikey)
        self.timestamp = timestamp

    def crawl(self):
        newts = datetime.now()
        elapsed = newts - self.timestamp
        if elapsed < timedelta(hours=1):
            self.logger.info(
                'Not an hour has passed since last crawled, not doing anything.'
            )
            return
        self.logger.info('Start crawling.')
        total = 0
        query = {
            'f1': 'days_elapsed', 'o1': 'lessthaneq', 'v1': str(elapsed.days + 1),
            'f2': 'attachments.ispatch', 'o2': 'equals', 'v2': '1'
        }
        bugs = self.bz.query(query)
        self.logger.info(f'Found {len(bugs)} bugs with patch attachments '
                         f'that were modified in the last {elapsed.days} day(s).')
        while bugs:
            bug = bugs[0]
            try:
                attachments = bug.get_attachments()
            except HTTPError as error:
                if error.args[0].startswith('429 Client Error: Too Many Requests'):
                    self.logger.warning('Got an HTTP 429 error, throttling requests.')
                    time.sleep(1)
                    continue
            else:
                bugs.pop(0)
                for attachment in attachments:
                    if not attachment['is_patch']:
                        continue
                    lastchange = datetime.fromisoformat(attachment['last_change_time'].value)
                    if lastchange <= self.timestamp:
                        continue
                    if self.store.add(
                        attachment['file_name'],
                        attachment['data'].data,
                        self.name,
                        bug.weburl,
                        lastchange.isoformat(sep=' ')
                    ):
                        total += 1
        self.logger.info(f'Done crawling, added {total} patches.')
        self.timestamp = newts


if __name__ == '__main__':
    default_instance = 'https://bugzilla.opensuse.org'
    parser = argparse.ArgumentParser(description='Sample Bugzilla Patch Crawler.')
    parser.add_argument('--instance', '-i', metavar='instance',
                        help=f'an optional Bugzilla instance URL (defaults to {default_instance})')
    parser.add_argument('--api-key', '-k', metavar='apikey',
                        help='an optional Bugzilla API key (see https://bugzilla.readthedocs.org/en/5.0/api/core/v1/general.html#authentication)')
    parser.add_argument('--output-file', '-o', metavar='outfile',
                        help='an optional file path to write the Patch Store database to (a temporary file will be used if not specified)')
    parser.add_argument('--time-delta', '-t', metavar='delta',
                        help='an optional time delta (specified in days, defaults to 1)')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.output_file is None:
        dbfile, filepath = tempfile.mkstemp(suffix='.db')
        os.close(dbfile)
    else:
        filepath = args.output_file
    store = PatchStore(filepath)

    instance = args.instance or default_instance
    timestamp = datetime.now() - timedelta(days=int(args.time_delta or 1), seconds=1)
    crawler = BugzillaPatchCrawler(store, instance, args.api_key, timestamp)
    crawler.crawl()
