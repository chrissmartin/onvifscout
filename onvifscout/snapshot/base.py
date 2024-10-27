import xml.etree.ElementTree as ET
from datetime import time
from typing import Dict, Optional, Tuple

import requests
import urllib3
from requests.auth import HTTPDigestAuth

from ..utils import Logger

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ONVIFSnapshotBase:
    def __init__(self, timeout: int = 5, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self._namespaces = {
            "s": "http://www.w3.org/2003/05/soap-envelope",
            "trt": "http://www.onvif.org/ver10/media/wsdl",
            "tt": "http://www.onvif.org/ver10/schema",
            "tr2": "http://www.onvif.org/ver20/media/wsdl",
        }
        self.session = requests.Session()
        self.session.verify = False

    def _create_get_profiles_message(self) -> str:
        """Create SOAP message for GetProfiles request"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body>
        <GetProfiles xmlns="http://www.onvif.org/ver10/media/wsdl"/>
    </s:Body>
</s:Envelope>"""

    def _create_get_snapshot_uri_message(self, profile_token: str) -> str:
        """Create SOAP message for GetSnapshotUri request"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body>
        <GetSnapshotUri xmlns="http://www.onvif.org/ver10/media/wsdl">
            <ProfileToken>{profile_token}</ProfileToken>
        </GetSnapshotUri>
    </s:Body>
</s:Envelope>"""

    def _is_valid_image(self, data: bytes) -> bool:
        """Validate image data format"""
        if data.startswith(b"\xff\xd8\xff"):  # JPEG header
            return True
        if data.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG header
            return True
        return False

    def _try_snapshot_url(
        self, url: str, auth: Tuple[str, str, str], headers: Dict[str, str]
    ) -> Optional[bytes]:
        """Enhanced snapshot URL testing with better error handling"""
        auth_handler = (
            HTTPDigestAuth(auth[0], auth[1])
            if auth[2] == "Digest"
            else (auth[0], auth[1])
        )

        response = None
        for attempt in range(self.max_retries):
            try:
                # Add random parameter to bypass cache
                cache_buster = f"nocache={int(time.time())}"
                url_with_cache_buster = (
                    f"{url}{'&' if '?' in url else '?'}{cache_buster}"
                )

                response = self.session.get(
                    url_with_cache_buster,
                    auth=auth_handler,
                    timeout=min(3, self.timeout),
                    headers=headers,
                    stream=True,
                    allow_redirects=True,  # Follow redirects
                )

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "").lower()
                    if "image/" in content_type:
                        content = response.content
                        if self._is_valid_image(content):
                            Logger.success(f"Found working snapshot URL: {url}")
                            return content
                        else:
                            Logger.debug(f"Invalid image data from {url}")
                    else:
                        Logger.debug(
                            f"Non-image content type ({content_type}) from {url}"
                        )
                elif response.status_code == 401:
                    Logger.debug(f"Authentication failed for {url}")
                    break
                else:
                    Logger.debug(f"HTTP {response.status_code} received from {url}")

                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff

            except requests.exceptions.Timeout:
                Logger.debug(f"Timeout accessing {url}")
            except requests.exceptions.RequestException as e:
                Logger.debug(f"Error accessing {url}: {str(e)}")
            finally:
                if response:
                    response.close()

        return None

    def _create_soap_request(
        self, url: str, soap_message: str, auth: Tuple[str, str, str]
    ) -> Optional[ET.Element]:
        """Send SOAP request and return parsed XML response"""
        try:
            auth_handler = (
                HTTPDigestAuth(auth[0], auth[1])
                if auth[2] == "Digest"
                else (auth[0], auth[1])
            )

            response = self.session.post(
                url,
                auth=auth_handler,
                data=soap_message,
                headers={"Content-Type": "application/soap+xml"},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                return ET.fromstring(response.text)

        except Exception as e:
            Logger.debug(f"SOAP request failed: {str(e)}")

        return None
