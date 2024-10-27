import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from urllib.parse import urlparse

from ..utils import Logger


class MediaProfileHandler:
    def __init__(self, namespaces: Dict[str, str]):
        self._namespaces = namespaces

    def _create_get_stream_uri_message(self, profile_token: str) -> str:
        """Create SOAP message for GetStreamUri request"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body>
        <GetStreamUri xmlns="http://www.onvif.org/ver10/media/wsdl">
            <StreamSetup>
                <Stream xmlns="http://www.onvif.org/ver10/schema">RTP-Unicast</Stream>
                <Transport xmlns="http://www.onvif.org/ver10/schema">
                    <Protocol>RTSP</Protocol>
                </Transport>
            </StreamSetup>
            <ProfileToken>{profile_token}</ProfileToken>
        </GetStreamUri>
    </s:Body>
</s:Envelope>"""

    def get_media_profiles(self, soap_response: ET.Element) -> List[Dict[str, str]]:
        """Extract media profiles from SOAP response"""
        profiles = []
        try:
            # Try multiple approaches to find profiles
            profile_elements = (
                soap_response.findall(".//trt:Profiles", self._namespaces)
                or soap_response.findall(".//tt:Profiles", self._namespaces)
                or soap_response.findall(".//*[local-name()='Profiles']")
                or soap_response.findall(".//*[local-name()='Profile']")
            )

            for profile in profile_elements:
                profile_info = {
                    "token": profile.get("token", ""),
                    "name": profile.get("name", ""),
                }
                if profile_info["token"]:
                    profiles.append(profile_info)
                    Logger.debug(f"Found profile: {profile_info}")

        except Exception as e:
            Logger.debug(f"Error parsing media profiles: {str(e)}")

        return profiles

    def extract_uri_from_response(self, soap_response: ET.Element) -> Optional[str]:
        """Extract URI from SOAP response"""
        try:
            uri_element = soap_response.find(".//*[local-name()='Uri']")
            if uri_element is not None and uri_element.text:
                return uri_element.text
        except Exception as e:
            Logger.debug(f"Error extracting URI from response: {str(e)}")
        return None

    def normalize_rtsp_url(self, url: str, device_host: str) -> str:
        """Normalize RTSP URL to ensure it's fully qualified"""
        if not url.startswith("rtsp://"):
            # Handle relative URLs
            return (
                f"rtsp://{device_host}:{554}{url if url.startswith('/') else '/' + url}"
            )

        # Parse the URL to check components
        parsed = urlparse(url)
        if not parsed.port:
            # Add default RTSP port if missing
            parts = list(parsed)
            parts[1] = f"{parsed.hostname}:554"
            return parsed.scheme + "://" + parts[1] + parsed.path

        return url
