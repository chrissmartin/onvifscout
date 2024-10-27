import xml.etree.ElementTree as ET
from typing import Dict, Set
from urllib.parse import urlparse

from ..utils import Logger


class CapabilityDetector:
    def __init__(self, namespaces: Dict[str, str]):
        self._namespaces = namespaces

    def _create_get_capabilities_message(self) -> str:
        """Create SOAP message for GetCapabilities request"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body>
        <tds:GetCapabilities xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
            <tds:Category>Media</tds:Category>
            <tds:Category>Imaging</tds:Category>
        </tds:GetCapabilities>
    </s:Body>
</s:Envelope>"""

    def _extract_snapshot_capabilities(
        self, soap_response: ET.Element
    ) -> Dict[str, bool]:
        """Extract snapshot-related capabilities from SOAP response"""
        capabilities = {}
        try:
            # Look for media capabilities
            media = soap_response.find(
                ".//trt:Media", self._namespaces
            ) or soap_response.find(".//*[local-name()='Media']")

            if media is not None:
                # Check for snapshot support
                snapshot = media.find(
                    ".//tt:SnapshotUri", self._namespaces
                ) or media.find(".//*[local-name()='SnapshotUri']")
                capabilities["SupportsSnapshot"] = snapshot is not None

                # Check for JPEG support
                jpeg = media.find(".//tt:JPEG", self._namespaces) or media.find(
                    ".//*[local-name()='JPEG']"
                )
                capabilities["SupportsJPEG"] = jpeg is not None

                # Check for H264 support (for RTSP)
                h264 = media.find(".//tt:H264", self._namespaces) or media.find(
                    ".//*[local-name()='H264']"
                )
                capabilities["SupportsH264"] = h264 is not None

            # Look for imaging capabilities
            imaging = soap_response.find(
                ".//timg:Imaging", self._namespaces
            ) or soap_response.find(".//*[local-name()='Imaging']")
            if imaging is not None:
                capabilities["SupportsImaging"] = True

        except Exception as e:
            Logger.debug(f"Error extracting capabilities: {str(e)}")

        return capabilities

    def get_snapshot_endpoints(
        self, device_url: str, soap_response: ET.Element
    ) -> Set[str]:
        """Extract potential snapshot endpoints from capabilities"""
        endpoints = set()
        try:
            parsed = urlparse(device_url)
            base_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"

            # Look for snapshot URI in capabilities
            snapshot_elements = soap_response.findall(
                ".//*[local-name()='SnapshotUri']"
            )
            for elem in snapshot_elements:
                uri = elem.find(".//*[local-name()='Uri']")
                if uri is not None and uri.text:
                    # Handle both absolute and relative URIs
                    if uri.text.startswith("http"):
                        endpoints.add(uri.text)
                    else:
                        endpoints.add(f"{base_url}{uri.text}")

            # Add common snapshot endpoints based on found capabilities
            common_paths = [
                "/onvif/snapshot",
                "/onvif/media/snapshot",
                "/onvif-http/snapshot",
                "/media/snapshot",
                "/snapshot",
            ]
            endpoints.update(f"{base_url}{path}" for path in common_paths)

        except Exception as e:
            Logger.debug(f"Error getting snapshot endpoints: {str(e)}")

        return endpoints

    def get_stream_endpoints(
        self, device_url: str, soap_response: ET.Element
    ) -> Set[str]:
        """Extract potential streaming endpoints from capabilities"""
        endpoints = set()
        try:
            parsed = urlparse(device_url)
            hostname = parsed.hostname

            # Look for stream URI in capabilities
            stream_elements = soap_response.findall(
                ".//*[local-name()='StreamingUri']"
            ) or soap_response.findall(".//*[local-name()='StreamUri']")

            for elem in stream_elements:
                uri = elem.find(".//*[local-name()='Uri']")
                if uri is not None and uri.text:
                    if uri.text.startswith("rtsp"):
                        endpoints.add(uri.text)
                    else:
                        endpoints.add(f"rtsp://{hostname}:554{uri.text}")

            # Add common RTSP endpoints
            common_paths = [
                "/onvif/media/video1",
                "/onvif/video",
                "/live/main",
                "/live/ch1",
                "/stream1",
                "/h264",
            ]
            endpoints.update(f"rtsp://{hostname}:554{path}" for path in common_paths)

        except Exception as e:
            Logger.debug(f"Error getting stream endpoints: {str(e)}")

        return endpoints
