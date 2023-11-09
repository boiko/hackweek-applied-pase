from urllib3.exceptions import ProtocolError
from requests.exceptions import ConnectionError, RequestException

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
        except (ProtocolError , ConnectionError):
            if tries > 0:
                tries = tries - 1
                pass
            else:
                raise
