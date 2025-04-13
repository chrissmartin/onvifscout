import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union

from ..utils import Logger
from .namespaces import SOAP_NAMESPACES


class SOAPParser:
    @staticmethod
    def find_all_elements(root: ET.Element, tag_name: str) -> List[ET.Element]:
        """Find elements using multiple approaches"""
        elements = []

        # Try with each namespace
        for ns_prefix, ns_uri in SOAP_NAMESPACES.items():
            try:
                found = root.findall(f".//{ns_prefix}:{tag_name}", SOAP_NAMESPACES)
                elements.extend(found)
            except Exception as e:
                Logger.debug(f"Error searching with namespace {ns_prefix}: {str(e)}")

        # Try without namespace using local-name
        try:
            found = root.findall(f".//*[local-name()='{tag_name}']")
            elements.extend(found)
        except Exception as e:
            Logger.debug(f"Error searching without namespace: {str(e)}")

        return list(set(elements))  # Remove duplicates

    @staticmethod
    def extract_service_name(namespace: str) -> str:
        """Extract meaningful service name from namespace URL"""
        patterns = [
            r"ver\d+/([^/]+)/wsdl",
            r"ver\d+/([^/]+)",
            r"/([^/]+)$",
            r"org/([^/]+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, namespace)
            if match:
                name = match.group(1)
                name = re.sub(
                    r"(Service|WSDL|Interface)$", "", name, flags=re.IGNORECASE
                )
                return name.strip()

        return namespace.split("/")[-1]

    @staticmethod
    def parse_capabilities(element: ET.Element) -> Dict[str, Union[bool, str]]:
        """Parse capability XML element"""
        capabilities = {}

        for elem in element.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if tag in ["Extension", "Capabilities"]:
                continue

            if elem.text:
                if elem.text.lower() in ["true", "false"]:
                    capabilities[tag] = elem.text.lower() == "true"
                else:
                    capabilities[tag] = elem.text

        return capabilities

    @staticmethod
    def parse_discovery_response(response: str) -> Optional[Dict[str, List[str]]]:
        """Parse WS-Discovery probe response"""
        try:
            root = ET.fromstring(response)

            xaddrs = root.find(".//d:XAddrs", SOAP_NAMESPACES)
            types = root.find(".//d:Types", SOAP_NAMESPACES)

            if xaddrs is None or types is None:
                xaddrs = root.find(".//*[local-name()='XAddrs']")
                types = root.find(".//*[local-name()='Types']")

            if xaddrs is not None and types is not None:
                return {
                    "urls": xaddrs.text.split() if xaddrs.text else [],
                    "types": types.text.split() if types.text else [],
                }
        except ET.ParseError as e:
            Logger.error(f"Failed to parse discovery response: {str(e)}")

        return None
