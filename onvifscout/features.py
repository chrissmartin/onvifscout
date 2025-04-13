from typing import Dict, Optional, Set, Tuple

import urllib3

from .models import ONVIFCapabilities, ONVIFDevice
from .soap import SOAPClient, SOAPMessageBuilder, SOAPParser
from .utils import Logger

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ONVIFFeatureDetector:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.soap_client = SOAPClient(timeout=timeout)

    def _extract_service_name(self, namespace: str) -> str:
        """Extract meaningful service name from namespace URL with enhanced patterns"""
        return SOAPParser.extract_service_name(namespace)

    def _get_services(self, url: str, auth: Tuple[str, str, str]) -> Set[str]:
        """Get device services with enhanced error handling and parsing"""
        try:
            # Create and send SOAP request
            soap_message = SOAPMessageBuilder.create_get_services()
            root = self.soap_client.send_request(url, soap_message, auth)

            if not root:
                return set()

            services = set()
            search_patterns = [
                ".//tds:Service",
                ".//wsdl:Service",
                ".//*[local-name()='Service']",
                ".//*[local-name()='XAddr']",
                ".//*[local-name()='Namespace']",
            ]

            for pattern in search_patterns:
                try:
                    elements = SOAPParser.find_all_elements(
                        root, pattern.split(":")[-1]
                    )
                    if elements:
                        for service in elements:
                            # Try getting from Namespace element
                            ns_elem = SOAPParser.find_all_elements(service, "Namespace")
                            if ns_elem and ns_elem[0].text:
                                service_info = self._extract_service_name(
                                    ns_elem[0].text
                                )
                                if service_info:
                                    services.add(service_info)
                                    Logger.debug(f"Found service: {service_info}")

                            # Try getting from XAddr if no namespace
                            if not service_info:
                                xaddr = SOAPParser.find_all_elements(service, "XAddr")
                                if xaddr and xaddr[0].text:
                                    service_info = self._extract_service_name(
                                        xaddr[0].text
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

    def _get_capabilities(
        self, url: str, auth: Tuple[str, str, str]
    ) -> Dict[str, Dict[str, bool]]:
        """Get device capabilities with enhanced error handling and debugging"""
        try:
            Logger.debug(f"\nSending GetCapabilities request to {url}")

            # Create and send SOAP request
            soap_message = SOAPMessageBuilder.create_get_capabilities()
            root = self.soap_client.send_request(url, soap_message, auth)

            if not root:
                return {}

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
            caps_containers = SOAPParser.find_all_elements(root, "Capabilities")
            if not caps_containers:
                caps_containers = SOAPParser.find_all_elements(
                    root, "GetCapabilitiesResponse"
                )

            if caps_containers:
                caps_root = caps_containers[0]
                Logger.debug(f"Found capabilities container: {caps_root.tag}")

                # Process each category
                for category, tag_names in categories.items():
                    for tag_name in tag_names:
                        elements = SOAPParser.find_all_elements(caps_root, tag_name)
                        if elements:
                            capabilities[category] = SOAPParser.parse_capabilities(
                                elements[0]
                            )
                            Logger.debug(
                                f"Parsed {category} capabilities: {capabilities[category]}"  # noqa: E501
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
            # Create and send SOAP request
            soap_message = SOAPMessageBuilder.create_get_device_info()
            root = self.soap_client.send_request(url, soap_message, auth)

            if not root:
                return None

            # Try multiple approaches to find device info
            manufacturer = None
            model = None

            # Find manufacturer and model elements
            manufacturer_elements = SOAPParser.find_all_elements(root, "Manufacturer")
            model_elements = SOAPParser.find_all_elements(root, "Model")

            if manufacturer_elements and model_elements:
                manufacturer = manufacturer_elements[0].text
                model = model_elements[0].text
                if manufacturer and model:
                    return f"{manufacturer} {model}".strip()

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

    def __del__(self):
        """Cleanup resources"""
        self.soap_client.close()
