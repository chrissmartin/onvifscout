import time
import xml.etree.ElementTree as ET
from typing import Optional, Tuple

import requests
import urllib3
from requests.auth import HTTPDigestAuth

from onvifscout.utils import Logger

from .constants import (
    DEFAULT_SOAP_TIMEOUT,
    MAX_RETRIES,
    SOAP_CONTENT_TYPE,
    SOAP_USER_AGENT,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SOAPClient:
    def __init__(
        self, timeout: int = DEFAULT_SOAP_TIMEOUT, max_retries: int = MAX_RETRIES
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(
            {"Content-Type": SOAP_CONTENT_TYPE, "User-Agent": SOAP_USER_AGENT}
        )

    def send_request(
        self, url: str, message: str, auth: Tuple[str, str, str], **kwargs
    ) -> Optional[ET.Element]:
        """Send SOAP request and return parsed XML response"""
        auth_handler = (
            HTTPDigestAuth(auth[0], auth[1])
            if auth[2] == "Digest"
            else (auth[0], auth[1])
        )

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    url, auth=auth_handler, data=message, timeout=self.timeout, **kwargs
                )

                if response.status_code == 200:
                    return ET.fromstring(response.text)

                if response.status_code == 401:  # Authentication failed
                    break

            except requests.exceptions.RequestException as e:
                Logger.debug(f"Request failed (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                continue

        return None

    def close(self):
        """Close the session"""
        self.session.close()
