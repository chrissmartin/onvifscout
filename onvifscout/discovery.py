# discovery.py
import socket
import uuid
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import time

from .models import ONVIFDevice
from .utils import Logger


class ONVIFDiscovery:
    def __init__(self, timeout: int = 3, retries: int = 2):
        self.multicast_addr = "239.255.255.250"
        self.port = 3702
        self.timeout = timeout
        self.retries = retries
        self._namespaces = {
            "s": "http://www.w3.org/2003/05/soap-envelope",
            "a": "http://schemas.xmlsoap.org/ws/2004/08/addressing",
            "d": "http://schemas.xmlsoap.org/ws/2005/04/discovery",
            "dn": "http://www.onvif.org/ver10/network/wsdl",
        }

    def _create_probe_message(self) -> str:
        """Create WS-Discovery probe message with multiple device types"""
        message_uuid = uuid.uuid4()
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <s:Envelope
            xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
            <s:Header>
                <a:Action s:mustUnderstand="1">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</a:Action>
                <a:MessageID>urn:uuid:{message_uuid}</a:MessageID>
                <a:To s:mustUnderstand="1">urn:schemas-xmlsoap-org:ws:2005:04:discovery</a:To>
            </s:Header>
            <s:Body>
                <d:Probe>
                    <d:Types>dn:NetworkVideoTransmitter tds:Device</d:Types>
                </d:Probe>
            </s:Body>
        </s:Envelope>"""

    def _parse_probe_response(self, response: str) -> Optional[Dict]:
        """Parse WS-Discovery probe response with enhanced error handling"""
        try:
            root = ET.fromstring(response)
            ns = self._namespaces

            # Try multiple possible XPath patterns for device info
            xaddrs = None
            types = None

            # Try standard ONVIF format
            xaddrs = root.find(".//d:XAddrs", ns)
            types = root.find(".//d:Types", ns)

            # If not found, try without namespace
            if xaddrs is None:
                xaddrs = root.find(".//*[local-name()='XAddrs']")
            if types is None:
                types = root.find(".//*[local-name()='Types']")

            if xaddrs is None or types is None:
                Logger.warning(f"Incomplete device information in response: {response}")
                return None

            return {
                "urls": xaddrs.text.split() if xaddrs.text else [],
                "types": types.text.split() if types.text else [],
            }
        except ET.ParseError as e:
            Logger.error(f"Failed to parse discovery response: {str(e)}")
            Logger.debug(f"Response content: {response}")
            return None
        except Exception as e:
            Logger.error(f"Unexpected error parsing discovery response: {str(e)}")
            return None

    def discover(self) -> List[ONVIFDevice]:
        """Discover ONVIF devices with retry mechanism"""
        Logger.header("Starting ONVIF device discovery...")
        devices = {}  # Use dict to avoid duplicates

        for attempt in range(self.retries):
            if attempt > 0:
                Logger.info(f"Retry attempt {attempt + 1}/{self.retries}")

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    # Enable broadcasting and reuse address
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

                    # Some devices need a larger receive buffer
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 512000)

                    sock.settimeout(self.timeout)
                    sock.bind(("", self.port))

                    # Send probe message
                    probe_message = self._create_probe_message()
                    sock.sendto(
                        probe_message.encode(), (self.multicast_addr, self.port)
                    )

                    # Wait a bit to let devices respond
                    time.sleep(0.5)

                    # Collect responses
                    while True:
                        try:
                            data, addr = sock.recvfrom(8192)  # Increased buffer size
                            response = data.decode("utf-8", errors="ignore")
                            device_info = self._parse_probe_response(response)

                            if device_info and device_info["urls"]:
                                if addr[0] not in devices:
                                    Logger.success(f"Found device at {addr[0]}")
                                    devices[addr[0]] = ONVIFDevice(
                                        address=addr[0],
                                        urls=device_info["urls"],
                                        types=device_info["types"],
                                    )
                        except socket.timeout:
                            break
                        except Exception as e:
                            Logger.error(f"Error processing device response: {str(e)}")
                            continue

            except Exception as e:
                Logger.error(f"Discovery error: {str(e)}")
                continue

        return list(devices.values())
