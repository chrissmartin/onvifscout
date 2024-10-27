# snapshot.py
import os
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from requests.auth import HTTPDigestAuth

from .device_contexts import DeviceContext, DeviceContextManager
from .models import ONVIFDevice
from .utils import Logger


class ONVIFSnapshot:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self._namespaces = {
            "s": "http://www.w3.org/2003/05/soap-envelope",
            "trt": "http://www.onvif.org/ver10/media/wsdl",
            "tt": "http://www.onvif.org/ver10/schema",
            "tr2": "http://www.onvif.org/ver20/media/wsdl",
        }

    def _create_get_profiles_message(self) -> str:
        """Create SOAP message for GetProfiles request"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body>
        <GetProfiles xmlns="http://www.onvif.org/ver10/media/wsdl"/>
    </s:Body>
</s:Envelope>"""

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

    def _get_media_profiles(
        self, device: ONVIFDevice, auth: Tuple[str, str, str]
    ) -> List[Dict[str, str]]:
        """Get available media profiles from the device"""
        try:
            context = DeviceContextManager.get_context(device.name)
            parsed = urllib.parse.urlparse(device.urls[0])

            # Try each media service endpoint
            for service_path in context.media_services:
                media_url = (
                    f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{service_path}"
                )

                try:
                    auth_handler = (
                        HTTPDigestAuth(auth[0], auth[1])
                        if auth[2] == "Digest"
                        else (auth[0], auth[1])
                    )
                    response = requests.post(
                        media_url,
                        auth=auth_handler,
                        data=self._create_get_profiles_message(),
                        headers={"Content-Type": "application/soap+xml"},
                        timeout=self.timeout,
                        verify=False,
                    )

                    if response.status_code == 200:
                        root = ET.fromstring(response.text)
                        profiles = []

                        # Try multiple approaches to find profiles
                        profile_elements = (
                            root.findall(".//trt:Profiles", self._namespaces)
                            or root.findall(".//tt:Profiles", self._namespaces)
                            or root.findall(".//*[local-name()='Profiles']")
                            or root.findall(".//*[local-name()='Profile']")
                        )

                        for profile in profile_elements:
                            profile_info = {
                                "token": profile.get("token", ""),
                                "name": profile.get("name", ""),
                            }

                            if profile_info["token"]:
                                profiles.append(profile_info)
                                Logger.debug(f"Found profile: {profile_info}")

                        if profiles:
                            return profiles

                except Exception as e:
                    Logger.debug(f"Failed to get profiles from {media_url}: {str(e)}")
                    continue

            Logger.warning("No media profiles found")
            return []

        except Exception as e:
            Logger.error(f"Error getting media profiles: {str(e)}")
            return []

    def _get_rtsp_stream_url(
        self, device: ONVIFDevice, auth: Tuple[str, str, str], profile_token: str
    ) -> Optional[str]:
        """Get RTSP stream URL for a profile"""
        try:
            context = DeviceContextManager.get_context(device.name)
            parsed = urllib.parse.urlparse(device.urls[0])

            # Try each media service endpoint
            for service_path in context.media_services:
                media_url = (
                    f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{service_path}"
                )

                try:
                    auth_handler = (
                        HTTPDigestAuth(auth[0], auth[1])
                        if auth[2] == "Digest"
                        else (auth[0], auth[1])
                    )
                    response = requests.post(
                        media_url,
                        auth=auth_handler,
                        data=self._create_get_stream_uri_message(profile_token),
                        headers={"Content-Type": "application/soap+xml"},
                        timeout=self.timeout,
                        verify=False,
                    )

                    if response.status_code == 200:
                        root = ET.fromstring(response.text)
                        uri_element = root.find(".//*[local-name()='Uri']")

                        if uri_element is not None and uri_element.text:
                            rtsp_url = uri_element.text
                            if not rtsp_url.startswith("rtsp://"):
                                rtsp_url = f"rtsp://{parsed.hostname}:{554}{rtsp_url}"
                            return rtsp_url

                except Exception as e:
                    Logger.debug(f"Failed to get RTSP URL from {media_url}: {str(e)}")
                    continue

            return None

        except Exception as e:
            Logger.debug(f"Error getting RTSP stream URL: {str(e)}")
            return None

    def _try_snapshot_url(
        self, url: str, auth: Tuple[str, str, str], headers: Dict[str, str]
    ) -> bool:
        """Try a single snapshot URL"""
        try:
            Logger.debug(f"Trying snapshot URL: {url}")
            auth_handler = (
                HTTPDigestAuth(auth[0], auth[1])
                if auth[2] == "Digest"
                else (auth[0], auth[1])
            )

            response = requests.get(
                url,
                auth=auth_handler,
                timeout=self.timeout,
                verify=False,
                headers=headers,
                stream=True,
            )

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                content_length = int(response.headers.get("content-length", "0"))

                if content_type.startswith("image/") and content_length > 1000:
                    Logger.success(f"Found working snapshot URL: {url}")
                    response.close()
                    return True

            response.close()
            return False

        except Exception as e:
            Logger.debug(f"Failed trying {url}: {str(e)}")
            return False

    def _try_device_urls(
        self, device: ONVIFDevice, context: DeviceContext, auth: Tuple[str, str, str]
    ) -> Optional[str]:
        """Try snapshot URLs for a specific device context"""
        headers = {
            "Accept": "image/jpeg,image/*",
            "User-Agent": "ONVIF Client/1.0",
            "Connection": "keep-alive",
        }

        parsed = urllib.parse.urlparse(device.urls[0])
        device_host = parsed.hostname
        device_port = parsed.port

        # Try each port and path combination
        ports = [device_port] + [p for p in context.ports if p != device_port]
        paths = DeviceContextManager.get_all_paths(context)

        for port in ports:
            for path in paths:
                url = f"{parsed.scheme}://{device_host}:{port}{path}"
                if self._try_snapshot_url(url, auth, headers):
                    return url

        return None

    def _capture_rtsp_frame(
        self, rtsp_url: str, auth: Tuple[str, str, str], output_path: str
    ) -> Optional[str]:
        """Capture a frame from RTSP stream using ffmpeg"""
        try:
            # Add credentials to RTSP URL
            parsed = urllib.parse.urlparse(rtsp_url)
            rtsp_url_with_auth = rtsp_url.replace(
                f"{parsed.scheme}://{parsed.hostname}",
                f"{parsed.scheme}://{auth[0]}:{auth[1]}@{parsed.hostname}",
            )

            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-rtsp_transport",
                "tcp",  # Use TCP (more reliable)
                "-i",
                rtsp_url_with_auth,
                "-frames:v",
                "1",  # Capture single frame
                "-q:v",
                "2",  # High quality
                "-f",
                "image2",  # Force image2 format
                output_path,
            ]

            # Run ffmpeg silently
            process = subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            if process.returncode == 0 and os.path.exists(output_path):
                Logger.success(f"RTSP snapshot saved to: {output_path}")
                return output_path

            return None

        except Exception as e:
            Logger.debug(f"Error capturing RTSP frame: {str(e)}")
            return None

    def capture_snapshot(
        self, device: ONVIFDevice, output_dir: str = "snapshots"
    ) -> Optional[str]:
        """Capture snapshot using device-specific context with RTSP fallback"""
        if not device.valid_credentials:
            Logger.error("No valid credentials available")
            return None

        os.makedirs(output_dir, exist_ok=True)
        cred = device.valid_credentials[
            0
        ]  # cred is tuple of (username, password, auth_type)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            output_dir, f"snapshot_{device.address}_{timestamp}.jpg"
        )

        try:
            # Get device context
            context = DeviceContextManager.get_context(device.name)
            Logger.info(f"Using {context.name} device context...")

            # Method 1: Try URL-based snapshot
            Logger.info("Attempting URL-based snapshot capture...")
            snapshot_url = self._try_device_urls(device, context, cred)

            if snapshot_url:
                auth_handler = (
                    HTTPDigestAuth(cred[0], cred[1])
                    if cred[2] == "Digest"
                    else (cred[0], cred[1])
                )
                response = requests.get(
                    snapshot_url,
                    auth=auth_handler,
                    timeout=self.timeout,
                    verify=False,
                    headers={"Accept": "image/jpeg,image/*"},
                )

                if response.status_code == 200 and response.headers.get(
                    "content-type", ""
                ).startswith("image/"):
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    Logger.success(f"Snapshot saved to: {output_path}")
                    return output_path

            # Method 2: Try RTSP stream capture
            Logger.info("URL-based snapshot failed, trying RTSP stream capture...")
            profiles = self._get_media_profiles(device, cred)

            for profile in profiles:
                Logger.debug(f"Trying RTSP with profile: {profile['token']}")
                rtsp_url = self._get_rtsp_stream_url(device, cred, profile["token"])

                if rtsp_url:
                    Logger.info(f"Found RTSP stream URL: {rtsp_url}")
                    result = self._capture_rtsp_frame(rtsp_url, cred, output_path)
                    if result:
                        return result

            Logger.error("Failed to capture snapshot through any method")
            return None

        except Exception as e:
            Logger.error(f"Error capturing snapshot: {str(e)}")
            Logger.debug(f"Full exception details: {repr(e)}")
            return None
