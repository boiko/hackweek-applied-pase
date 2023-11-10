# Copyright 2023 Gustavo Boiko
# This work is licensed under the GNU GPLv3 or later.
# See the COPYING file in the top-level directory.

from urllib3.exceptions import ProtocolError
from requests.exceptions import ConnectionError, RequestException

import logging

def session_get_with_retries(session, url, tries=4):
    """
    Sometimes downloads fail with connection drops or other temporary errors.
    This function catches the known exceptions and retries.

    :param session: A requests.sessions.Session instance to be used
    :param url: the URL to be retrieved
    :param tries: number of attempts to make
    :return: The response from session.get()
    """
    while tries > 0:
        try:
            return session.get(url)
        except (ProtocolError , ConnectionError) as e:
            if tries > 0:
                logging.warning(f"Request error, trying again: {str(e)}")
                tries = tries - 1
                pass
            else:
                raise
