import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple
import re

import requests
import urllib3
from requests.auth import HTTPDigestAuth

from .models import ONVIFCapabilities, ONVIFDevice
from .utils import Logger

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ONVIFFeatureDetector:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self._namespaces = {
            "s": "http://www.w3.org/2003/05/soap-envelope",
            "SOAP-ENV": "http://www.w3.org/2003/05/soap-envelope",
            "tds": "http://www.onvif.org/ver10/device/wsdl",
            "tt": "http://www.onvif.org/ver10/schema",
            "trt": "http://www.onvif.org/ver10/media/wsdl",
            "tev": "http://www.onvif.org/ver10/events/wsdl",
            "timg": "http://www.onvif.org/ver20/imaging/wsdl",
            "tptz": "http://www.onvif.org/ver20/ptz/wsdl",
            "tan": "http://www.onvif.org/ver20/analytics/wsdl",
            "tr2": "http://www.onvif.org/ver20/media/wsdl",
            # Add more namespaces that might be used by different cameras
            "wsdl": "http://schemas.xmlsoap.org/wsdl/",
            "wsnt": "http://docs.oasis-open.org/wsn/b-2",
            "xsd": "http://www.w3.org/2001/XMLSchema",
        }

    def _create_get_device_info_message(self) -> str:
        """Create SOAP message for GetDeviceInformation request"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <GetDeviceInformation xmlns="http://www.onvif.org/ver10/device/wsdl"/>
    </s:Body>
</s:Envelope>"""

    def _create_get_services_message(self) -> str:
        """Create SOAP message for GetServices request"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body>
        <tds:GetServices xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
            <tds:IncludeCapability>true</tds:IncludeCapability>
        </tds:GetServices>
    </s:Body>
</s:Envelope>"""

    def _create_get_capabilities_message(self) -> str:
        """Create SOAP message for GetCapabilities request"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body>
        <tds:GetCapabilities xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
            <tds:Category>All</tds:Category>
        </tds:GetCapabilities>
    </s:Body>
</s:Envelope>"""

    def _log_response(self, response: requests.Response, request_type: str):
        """Log detailed response information for debugging"""
        Logger.debug(f"\n=== {request_type} Response ===")
        Logger.debug(f"Status Code: {response.status_code}")
        Logger.debug(f"Headers: {dict(response.headers)}")
        Logger.debug(f"Content: {response.text[:1000]}...")  # First 1000 chars

        try:
            root = ET.fromstring(response.text)
            Logger.debug(f"XML Structure:")
            self._log_xml_structure(root)
        except ET.ParseError as e:
            Logger.debug(f"Failed to parse XML: {str(e)}")

    def _log_xml_structure(self, element: ET.Element, level: int = 0):
        """Recursively log XML structure"""
        indent = "  " * level
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        attrs = [f"{k}='{v}'" for k, v in element.attrib.items()]
        attr_str = " ".join(attrs)

        if attr_str:
            Logger.debug(f"{indent}{tag} ({attr_str})")
        else:
            Logger.debug(f"{indent}{tag}")

        for child in element:
            self._log_xml_structure(child, level + 1)

    def _extract_service_name(self, namespace: str) -> str:
        """Extract meaningful service name from namespace URL with enhanced patterns"""
        patterns = [
            r"ver\d+/([^/]+)/wsdl",
            r"ver\d+/([^/]+)",
            r"/([^/]+)$",
            r"org/([^/]+)$",
            r"schemas\.xmlsoap\.org/([^/]+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, namespace)
            if match:
                name = match.group(1)
                # Clean up common suffixes
                name = re.sub(
                    r"(Service|WSDL|Interface)$", "", name, flags=re.IGNORECASE
                )
                return name.strip()

        return namespace.split("/")[-1]

    def _find_all_elements(self, root: ET.Element, tag_name: str) -> List[ET.Element]:
        """Find elements using multiple approaches"""
        elements = []

        # Try with each namespace
        for ns_prefix, ns_uri in self._namespaces.items():
            try:
                found = root.findall(f".//{ns_prefix}:{tag_name}", self._namespaces)
                elements.extend(found)
                if found:
                    Logger.debug(
                        f"Found {len(found)} elements with namespace {ns_prefix}"
                    )
            except Exception as e:
                Logger.debug(f"Error searching with namespace {ns_prefix}: {str(e)}")

        # Try without namespace using local-name
        try:
            found = root.findall(f".//*[local-name()='{tag_name}']")
            elements.extend(found)
            if found:
                Logger.debug(f"Found {len(found)} elements without namespace")
        except Exception as e:
            Logger.debug(f"Error searching without namespace: {str(e)}")

        # Try case-insensitive search
        try:
            found = root.findall(
                f".//*[translate(local-name(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{tag_name.lower()}']"
            )
            elements.extend([e for e in found if e not in elements])
            if found:
                Logger.debug(
                    f"Found {len(found)} elements with case-insensitive search"
                )
        except Exception as e:
            Logger.debug(f"Error in case-insensitive search: {str(e)}")

        return elements

    def _get_services(self, url: str, auth: Tuple[str, str, str]) -> Set[str]:
        """Get device services with enhanced error handling and parsing"""
        try:
            auth_handler = (
                HTTPDigestAuth(auth[0], auth[1])
                if auth[2] == "Digest"
                else (auth[0], auth[1])
            )

            response = requests.post(
                url,
                auth=auth_handler,
                data=self._create_get_services_message(),
                headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                timeout=self.timeout,
                verify=False,
            )

            if response.status_code != 200:
                return set()

            root = ET.fromstring(response.text)
            services = set()

            # Try multiple approaches to find services
            search_patterns = [
                # Standard ONVIF format
                ".//tds:Service",
                # Alternative namespace
                ".//wsdl:Service",
                # No namespace
                ".//*[local-name()='Service']",
                # Try finding by address
                ".//*[local-name()='XAddr']",
                # Try finding by namespace declaration
                ".//*[local-name()='Namespace']",
            ]

            for pattern in search_patterns:
                try:
                    elements = root.findall(pattern, self._namespaces)
                    if elements:
                        for service in elements:
                            # Try multiple ways to extract service info
                            service_info = None

                            # Try getting from Namespace element
                            ns_elem = service.find(".//*[local-name()='Namespace']")
                            if ns_elem is not None and ns_elem.text:
                                service_info = self._extract_service_name(ns_elem.text)

                            # Try getting from XAddr if no namespace
                            if not service_info:
                                xaddr = service.find(".//*[local-name()='XAddr']")
                                if xaddr is not None and xaddr.text:
                                    service_info = self._extract_service_name(
                                        xaddr.text
                                    )

                            if service_info:
                                services.add(service_info)
                                Logger.debug(f"Found service: {service_info}")

                except Exception as e:
                    Logger.debug(f"Pattern {pattern} failed: {str(e)}")
                    continue

            return services

        except Exception as e:
            Logger.debug(f"Service discovery error: {str(e)}")
            return set()

    def _parse_capabilities(self, element: ET.Element) -> Dict[str, bool]:
        """Parse capability XML element with enhanced debugging"""
        capabilities = {}
        Logger.debug(f"\nParsing capabilities from element: {element.tag}")

        for elem in element.iter():
            # Get the tag name without namespace
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # Skip certain container elements
            if tag in ["Extension", "Capabilities"]:
                continue

            # Process the value
            if elem.text:
                if elem.text.lower() in ["true", "false"]:
                    capabilities[tag] = elem.text.lower() == "true"
                    Logger.debug(
                        f"Added boolean capability: {tag} = {capabilities[tag]}"
                    )
                else:
                    capabilities[tag] = elem.text
                    Logger.debug(f"Added string capability: {tag} = {elem.text}")

            # Process attributes
            for attr_name, attr_value in elem.attrib.items():
                if attr_value.lower() in ["true", "false"]:
                    capabilities[attr_name] = attr_value.lower() == "true"
                    Logger.debug(
                        f"Added boolean attribute: {attr_name} = {capabilities[attr_name]}"
                    )
                else:
                    capabilities[attr_name] = attr_value
                    Logger.debug(f"Added string attribute: {attr_name} = {attr_value}")

        return capabilities

    def _get_capabilities(
        self, url: str, auth: Tuple[str, str, str]
    ) -> Dict[str, Dict[str, bool]]:
        """Get device capabilities with enhanced error handling and debugging"""
        try:
            auth_handler = (
                HTTPDigestAuth(auth[0], auth[1])
                if auth[2] == "Digest"
                else (auth[0], auth[1])
            )

            Logger.debug(f"\nSending GetCapabilities request to {url}")
            Logger.debug(f"Request Body:\n{self._create_get_capabilities_message()}")

            response = requests.post(
                url,
                auth=auth_handler,
                data=self._create_get_capabilities_message(),
                headers={
                    "Content-Type": "application/soap+xml; charset=utf-8",
                    "User-Agent": "ONVIF Client",
                },
                timeout=self.timeout,
                verify=False,
            )

            self._log_response(response, "GetCapabilities")

            if response.status_code != 200:
                return {}

            root = ET.fromstring(response.text)
            capabilities = {}

            # Map of capability categories with multiple possible tag names
            categories = {
                "analytics": ["Analytics", "AnalyticsCapabilities", "AnalyticsEngine"],
                "device": ["Device", "DeviceCapabilities", "DeviceIO"],
                "events": ["Events", "EventCapabilities", "EventPort"],
                "imaging": ["Imaging", "ImagingCapabilities", "ImagingSettings"],
                "media": ["Media", "MediaCapabilities", "MediaService"],
                "ptz": ["PTZ", "PTZCapabilities", "PTZService"],
            }

            # Find all possible Capabilities containers
            caps_containers = self._find_all_elements(root, "Capabilities")
            if not caps_containers:
                caps_containers = self._find_all_elements(
                    root, "GetCapabilitiesResponse"
                )

            if caps_containers:
                caps_root = caps_containers[0]
                Logger.debug(f"Found capabilities container: {caps_root.tag}")

                # Process each category
                for category, tag_names in categories.items():
                    for tag_name in tag_names:
                        elements = self._find_all_elements(caps_root, tag_name)
                        if elements:
                            capabilities[category] = self._parse_capabilities(
                                elements[0]
                            )
                            Logger.debug(
                                f"Parsed {category} capabilities: {capabilities[category]}"
                            )
                            break

            return capabilities

        except Exception as e:
            Logger.error(f"Error getting capabilities: {str(e)}")
            Logger.debug(f"Full exception: {repr(e)}")
            return {}

    def _get_device_info(self, url: str, auth: Tuple[str, str, str]) -> Optional[str]:
        """Get device information including name/model"""
        try:
            auth_handler = (
                HTTPDigestAuth(auth[0], auth[1])
                if auth[2] == "Digest"
                else (auth[0], auth[1])
            )

            Logger.debug(f"\nSending GetDeviceInformation request to {url}")

            response = requests.post(
                url,
                auth=auth_handler,
                data=self._create_get_device_info_message(),
                headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                timeout=self.timeout,
                verify=False,
            )

            if response.status_code != 200:
                return None

            root = ET.fromstring(response.text)

            # Try multiple approaches to find device info
            manufacturer = None
            model = None

            # Try with different namespaces
            for ns_prefix in ["tds", "tt"]:
                try:
                    manufacturer = root.find(
                        f".//{ns_prefix}:Manufacturer", self._namespaces
                    )
                    model = root.find(f".//{ns_prefix}:Model", self._namespaces)
                    if manufacturer is not None and model is not None:
                        break
                except Exception:
                    continue

            # Try without namespace if not found
            if manufacturer is None or model is None:
                manufacturer = root.find(".//*[local-name()='Manufacturer']")
                model = root.find(".//*[local-name()='Model']")

            if manufacturer is not None and model is not None:
                return f"{manufacturer.text} {model.text}".strip()

            return None

        except Exception as e:
            Logger.error(f"Error getting device info: {str(e)}")
            return None

    def detect_features(self, device: ONVIFDevice) -> None:
        """Detect features for a device with enhanced logging"""
        if not device.valid_credentials:
            Logger.warning("No valid credentials available for feature detection")
            return

        Logger.header(f"Detecting features for device {device.address}")
        Logger.debug(f"\nUsing URL: {device.urls[0]}")
        Logger.debug(f"Using credentials: {device.valid_credentials[0]}")

        cred = device.valid_credentials[0]
        url = device.urls[0]

        # Get device name first
        Logger.info("Fetching device information...")
        device_name = self._get_device_info(url, cred)
        if device_name:
            device.name = device_name
            Logger.success(f"Device name: {device_name}")
        else:
            Logger.warning("Could not fetch device name")

        capabilities = ONVIFCapabilities()

        Logger.info("Detecting supported services...")
        capabilities.services = self._get_services(url, cred)
        if not capabilities.services:
            Logger.warning(
                "No services detected. Device might not support service discovery."
            )

        Logger.info("Detecting device capabilities...")
        feature_caps = self._get_capabilities(url, cred)

        # Map capabilities to the device object
        for category, caps in feature_caps.items():
            setattr(capabilities, category, caps)

        device.capabilities = capabilities
