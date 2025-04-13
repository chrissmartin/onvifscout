import time
from typing import Dict, List, Optional, Tuple

import requests
import urllib3

from ..models import ONVIFDevice
from ..soap import SOAPClient, SOAPMessageBuilder, SOAPParser
from ..utils import Logger

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ONVIFSnapshotBase:
    """Base class for ONVIF snapshot functionality"""

    def __init__(self, timeout: int = 5, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize SOAP client
        self.soap_client = SOAPClient(timeout=timeout, max_retries=max_retries)

        # Initialize HTTP session for image downloads
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(
            {
                "User-Agent": "ONVIFSnapshot/1.0",
                "Accept": "image/jpeg, image/png, image/*",
            }
        )

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

        # Form the complete URL with cache buster
        cache_buster = f"nocache={int(time.time())}"
        url_with_cache_buster = f"{url}{'&' if '?' in url else '?'}{cache_buster}"

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url_with_cache_buster,
                    auth=self._get_auth_handler(auth),
                    timeout=min(3, self.timeout),
                    headers=headers,
                    stream=True,
                    allow_redirects=True,
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
                    break  # No need to retry on auth failure
                else:
                    Logger.debug(f"HTTP {response.status_code} received from {url}")

                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff

            except requests.exceptions.Timeout:
                Logger.debug(f"Timeout accessing {url}")
            except requests.exceptions.RequestException as e:
                Logger.debug(f"Error accessing {url}: {str(e)}")
            finally:
                if "response" in locals():
                    response.close()

        return None

    def _get_auth_handler(self, auth: Tuple[str, str, str]) -> Tuple[str, str]:
        """Get appropriate authentication handler based on auth type"""
        username, password, auth_type = auth
        return (
            requests.auth.HTTPDigestAuth(username, password)
            if auth_type == "Digest"
            else (username, password)
        )

    def get_media_profiles(self, device: ONVIFDevice) -> List[Dict[str, str]]:
        """Get media profiles for the device"""
        if not device.valid_credentials:
            Logger.debug("No valid credentials available for media profile retrieval")
            return []

        try:
            soap_message = SOAPMessageBuilder.create_get_profiles()
            root = self.soap_client.send_request(
                device.urls[0], soap_message, device.valid_credentials[0]
            )

            if not root:
                return []

            profiles = []
            profile_elements = SOAPParser.find_all_elements(root, "Profile")

            for profile in profile_elements:
                profile_info = {
                    "token": profile.get("token", ""),
                    "name": profile.get("name", ""),
                }
                if profile_info["token"]:
                    profiles.append(profile_info)
                    Logger.debug(f"Found profile: {profile_info}")

            return profiles

        except Exception as e:
            Logger.error(f"Error getting media profiles: {str(e)}")
            return []

    def get_snapshot_uri(
        self, device: ONVIFDevice, profile_token: str
    ) -> Optional[str]:
        """Get snapshot URI for a specific profile"""
        if not device.valid_credentials:
            Logger.debug("No valid credentials available for snapshot URI retrieval")
            return None

        try:
            soap_message = SOAPMessageBuilder.create_get_snapshot_uri(profile_token)
            root = self.soap_client.send_request(
                device.urls[0], soap_message, device.valid_credentials[0]
            )

            if not root:
                return None

            uri_elements = SOAPParser.find_all_elements(root, "Uri")
            if uri_elements and uri_elements[0].text:
                return uri_elements[0].text.strip()

            return None

        except Exception as e:
            Logger.error(f"Error getting snapshot URI: {str(e)}")
            return None

    def build_snapshot_request_headers(self, device: ONVIFDevice) -> Dict[str, str]:
        """Build headers for snapshot request"""
        return {
            "Accept": "image/jpeg, image/png, image/*",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "ONVIFSnapshot/1.0",
            "X-Device-Name": device.name or "Unknown",
            "X-Device-Address": device.address,
        }

    def estimate_snapshot_time(self, profile_count: int = 1) -> float:
        """Estimate time needed for snapshot capture"""
        base_time = 2.0  # Base processing time
        profile_time = 1.0  # Time to process each profile
        retry_overhead = 0.5  # Additional time for potential retries

        return (base_time + (profile_time * profile_count)) * (1 + retry_overhead)

    def __del__(self):
        """Cleanup resources"""
        try:
            self.session.close()
            self.soap_client.close()
        except Exception as e:
            Logger.debug(f"Error during cleanup: {str(e)}")
