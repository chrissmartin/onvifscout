from typing import Dict, Optional, Set, Tuple

from onvifscout.models import ONVIFDevice

from ..soap import SOAPClient, SOAPMessageBuilder, SOAPParser
from ..utils import Logger


class CapabilityDetector:
    def __init__(self, namespaces: Dict[str, str]):
        self._namespaces = namespaces
        self.soap_client = SOAPClient()
        self.soap_parser = SOAPParser()

    def _get_services(self, url: str, auth: Tuple[str, str, str]) -> Set[str]:
        """Get device services with enhanced error handling and parsing"""
        message = SOAPMessageBuilder.create_get_services()
        root = self.soap_client.send_request(url, message, auth)
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
                elements = root.findall(pattern, self._namespaces)
                if elements:
                    for service in elements:
                        service_info = None
                        ns_elem = service.find(".//*[local-name()='Namespace']")
                        if ns_elem is not None and ns_elem.text:
                            service_info = self.soap_parser.extract_service_name(
                                ns_elem.text
                            )

                        if not service_info:
                            xaddr = service.find(".//*[local-name()='XAddr']")
                            if xaddr is not None and xaddr.text:
                                service_info = self.soap_parser.extract_service_name(
                                    xaddr.text
                                )

                        if service_info:
                            services.add(service_info)
                            Logger.debug(f"Found service: {service_info}")

            except Exception as e:
                Logger.debug(f"Pattern {pattern} failed: {str(e)}")
                continue

        return services

    def _get_capabilities(
        self, url: str, auth: Tuple[str, str, str]
    ) -> Dict[str, Dict[str, bool]]:
        """Get device capabilities with enhanced error handling and debugging"""
        message = SOAPMessageBuilder.create_get_capabilities()
        root = self.soap_client.send_request(url, message, auth)
        if not root:
            return {}

        capabilities = {}
        categories = {
            "analytics": ["Analytics", "AnalyticsCapabilities", "AnalyticsEngine"],
            "device": ["Device", "DeviceCapabilities", "DeviceIO"],
            "events": ["Events", "EventCapabilities", "EventPort"],
            "imaging": ["Imaging", "ImagingCapabilities", "ImagingSettings"],
            "media": ["Media", "MediaCapabilities", "MediaService"],
            "ptz": ["PTZ", "PTZCapabilities", "PTZService"],
        }

        caps_containers = self.soap_parser.find_all_elements(root, "Capabilities")
        if not caps_containers:
            caps_containers = self.soap_parser.find_all_elements(
                root, "GetCapabilitiesResponse"
            )

        if caps_containers:
            caps_root = caps_containers[0]
            Logger.debug(f"Found capabilities container: {caps_root.tag}")

            for category, tag_names in categories.items():
                for tag_name in tag_names:
                    elements = self.soap_parser.find_all_elements(caps_root, tag_name)
                    if elements:
                        capabilities[category] = self.soap_parser.parse_capabilities(
                            elements[0]
                        )
                        Logger.debug(
                            f"Parsed {category} capabilities: {capabilities[category]}"
                        )
                        break

        return capabilities

    def _get_device_info(self, url: str, auth: Tuple[str, str, str]) -> Optional[str]:
        """Get device information including name/model"""
        message = SOAPMessageBuilder.create_get_device_info()
        root = self.soap_client.send_request(url, message, auth)
        if not root:
            return None

        manufacturer = root.find(".//tds:Manufacturer", self._namespaces)
        model = root.find(".//tds:Model", self._namespaces)

        if manufacturer is None or model is None:
            manufacturer = root.find(".//*[local-name()='Manufacturer']")
            model = root.find(".//*[local-name()='Model']")

        if manufacturer is not None and model is not None:
            return f"{manufacturer.text} {model.text}".strip()

        return None

    def detect_features(self, device: "ONVIFDevice") -> None:
        """Detect features for a device with enhanced logging"""
        if not device.valid_credentials:
            Logger.warning("No valid credentials available for feature detection")
            return

        Logger.header(f"Detecting features for device {device.address}")
        cred = device.valid_credentials[0]
        url = device.urls[0]

        try:
            # Get device name
            Logger.info("Fetching device information...")
            device_name = self._get_device_info(url, cred)
            if device_name:
                device.name = device_name
                Logger.success(f"Device name: {device_name}")
            else:
                Logger.warning("Could not fetch device name")

            # Get supported services
            Logger.info("Detecting supported services...")
            device.capabilities.services = self._get_services(url, cred)
            if not device.capabilities.services:
                Logger.warning(
                    "No services detected. Device might not support service discovery."
                )

            # Get capabilities
            Logger.info("Detecting device capabilities...")
            feature_caps = self._get_capabilities(url, cred)

            # Map capabilities to the device object
            for category, caps in feature_caps.items():
                setattr(device.capabilities, category, caps)

        except Exception as e:
            Logger.error(f"Error detecting features: {str(e)}")
        finally:
            self.soap_client.close()
