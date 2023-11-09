import base64
from collections import namedtuple
from datetime import datetime
import hashlib
import logging
import mimetypes
import os.path
import sqlite3


Patch = namedtuple('Patch', ('filename', 'content', 'checksum', 'origin', 'timestamp'))
Patch.decode_content = lambda self: base64.b64decode(self.content)


class PatchStore(object):

    """
    SQLite-backed store that stores patch files, associated metadata,
    and their origin.
    The content of the patch files are stored base64-encoded,
    along with a checksum, and an optional timestamp (in the ISO 8601 format).
    """

    def __init__(self, dbfile: str):
        self.dbfile = dbfile
        logging.info(f'Instantiating Patch Store backed by {dbfile}')
        if not os.path.exists(dbfile):
            logging.warn(f'DB file {dbfile} does not exist, creating it')
        self.db = sqlite3.connect(dbfile)
        with self.db:
            self.db.execute(
                'CREATE TABLE IF NOT EXISTS patches'
                '(filename TEXT, content BLOB, checksum TEXT, origin TEXT, timestamp TEXT)'
            )

    def add(self, filename: str, content: bytes, origin: str, timestamp=None):
        """
        Add (insert or update) a patch to the store.
        
        :param filename: The original filename of the patch
        :param content: The patch file contents
        :param origin: The origin of the patch (for example, if fetching from bugzilla, could be an issue ID or URL
        :param timestamp: Some optional timestamp reference for the file in ISO 8601 format
        
        :return: True if successful, False otherwise
        """
        if not filename:
            logging.error('Storing a patch requires a filename to identify the patch')
            return False
        if mimetypes.guess_type(filename)[0] not in ('text/x-diff', 'text/x-patch'):
            logging.error('Filename does not match that of a patch file')
            return False
        if not content:
            logging.error('Empty patch contents')
            return False
        if not origin:
            logging.error('Storing a patch requires a valid origin')
            return False
        if timestamp is not None:
            try:
                timestamp = datetime.fromisoformat(timestamp).isoformat(sep=' ')
            except ValueError:
                logging.error(f'Invalid timestamp format: {timestamp} (expects ISO 8601)')
                return False
        else:
            timestamp = datetime.now().isoformat(sep=' ')

        encoded_content = base64.b64encode(content)
        checksum = self.compute_checksum(encoded_content)

        if not self.exists(filename, origin):
            with self.db:
                self.db.execute(
                    'INSERT INTO patches(filename, content, checksum, origin, timestamp) '
                    'VALUES(?, ?, ?, ?, ?)',
                    (filename, encoded_content, checksum, origin, timestamp)
                )
            logging.info(f'Stored new patch: {filename} ({origin})')
        else:
            with self.db:
                self.db.execute(
                    'UPDATE patches SET content = ?, checksum = ?, timestamp = ? '
                    'WHERE filename = ? AND origin = ?',
                    (encoded_content, checksum, timestamp, filename, origin)
                )
            logging.info(f'Updated existing patch: {filename} ({origin})')

        return True

    def compute_checksum(self, encoded_content: bytes):
        hash = hashlib.sha256(encoded_content)
        return f'{hash.name}:{hash.hexdigest()}'

    def exists(self, filename: str, origin: str):
        """
        Check whether a patch matching a given filename and a given origin
        already exists in the store.
        """
        with self.db:
            cursor = self.db.execute(
                'SELECT * from patches WHERE filename = ? AND origin = ?',
                (filename, origin)
            )
            if cursor.fetchone():
                return True
        return False

    def _search_query(self, query, parameters):
        with self.db:
            cursor = self.db.execute(query, parameters)
            for row in cursor.fetchall():
                yield Patch(*row)

    def search_by_filename(self, filename: str):
        return self._search_query('SELECT * FROM patches WHERE filename = ?', (filename,))

    def search_by_origin(self, origin: str):
        return self._search_query('SELECT * FROM patches WHERE origin LIKE ? || "%"', (origin,))

    def search_by_content(self, content: bytes):
        encoded_content = base64.b64encode(content)
        checksum = self.compute_checksum(encoded_content)
        return self._search_query('SELECT * FROM patches WHERE checksum = ?', (checksum,))
