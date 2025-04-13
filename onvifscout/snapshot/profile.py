import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

from ..soap import SOAPClient, SOAPMessageBuilder, SOAPParser
from ..utils import Logger


class MediaProfileHandler:
    def __init__(self, namespaces: Dict[str, str]):
        self._namespaces = namespaces
        self.soap_client = SOAPClient()
        self.parser = SOAPParser()

    def get_media_profiles(self, soap_response: ET.Element) -> List[Dict[str, str]]:
        """Extract media profiles from SOAP response"""
        profiles = []
        try:
            profile_elements = self.parser.find_all_elements(soap_response, "Profiles")

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

    def get_stream_uri(
        self, url: str, profile_token: str, auth: tuple
    ) -> Optional[str]:
        """Get stream URI for a profile"""
        try:
            message = SOAPMessageBuilder.create_get_profiles()
            response = self.soap_client.send_request(url, message, auth)

            if response is not None:
                uri_element = response.find(".//*[local-name()='Uri']")
                if uri_element is not None and uri_element.text:
                    return uri_element.text
        except Exception as e:
            Logger.debug(f"Error getting stream URI: {str(e)}")
        return None

    def normalize_rtsp_url(self, url: str, device_host: str) -> str:
        """Normalize RTSP URL to ensure it's fully qualified"""
        if not url.startswith("rtsp://"):
            return (
                f"rtsp://{device_host}:554{url if url.startswith('/') else '/' + url}"
            )

        parts = url.split("://")
        if len(parts) == 2:
            host_path = parts[1].split("/", 1)
            host = host_path[0]
            path = host_path[1] if len(host_path) > 1 else ""

            if ":" not in host:
                host = f"{host}:554"

            return f"rtsp://{host}/{path}"

        return url
