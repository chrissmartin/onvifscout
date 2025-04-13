import socket
import time
from typing import Dict, List

import urllib3

from .models import ONVIFDevice
from .soap import SOAPMessageBuilder, SOAPParser
from .utils import Logger

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ONVIFDiscovery:
    """ONVIF device discovery using WS-Discovery protocol"""

    def __init__(self, timeout: int = 3, retries: int = 2):
        self.multicast_addr = "239.255.255.250"
        self.port = 3702
        self.timeout = timeout
        self.retries = retries

    def _create_discovery_socket(self) -> socket.socket:
        """Create and configure socket for discovery"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Enable broadcasting and reuse address
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Some devices need a larger receive buffer
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 512000)

        sock.settimeout(self.timeout)
        sock.bind(("", self.port))

        return sock

    def _collect_responses(self, sock: socket.socket) -> List[Dict[str, List[str]]]:
        """Collect and parse responses from devices"""
        responses = []
        seen_devices = set()  # Track unique device responses

        while True:
            try:
                data, addr = sock.recvfrom(8192)  # Increased buffer size
                ip_address = addr[0]

                # Skip if we've already processed a response from this IP
                if ip_address in seen_devices:
                    continue

                response = data.decode("utf-8", errors="ignore")
                device_info = SOAPParser.parse_discovery_response(response)

                if device_info and device_info["urls"]:
                    seen_devices.add(ip_address)
                    device_info["address"] = ip_address
                    responses.append(device_info)
                    Logger.success(f"Found device at {ip_address}")
                    Logger.debug(f"Device URLs: {', '.join(device_info['urls'])}")
                    Logger.debug(f"Device types: {', '.join(device_info['types'])}")

            except socket.timeout:
                break
            except Exception as e:
                Logger.error(f"Error processing device response: {str(e)}")
                continue

        return responses

    def _send_probe(self, sock: socket.socket) -> None:
        """Send WS-Discovery probe message"""
        try:
            probe_message = SOAPMessageBuilder.create_discovery_probe()
            sock.sendto(probe_message.encode(), (self.multicast_addr, self.port))
            Logger.debug("Sent discovery probe message")

            # Brief pause to allow devices to prepare responses
            time.sleep(0.1)

        except Exception as e:
            Logger.error(f"Error sending probe message: {str(e)}")
            raise

    def discover(self) -> List[ONVIFDevice]:
        """Discover ONVIF devices with retry mechanism"""
        Logger.header("Starting ONVIF device discovery...")
        devices = {}  # Use dict to avoid duplicates

        for attempt in range(self.retries):
            if attempt > 0:
                Logger.info(f"Retry attempt {attempt + 1}/{self.retries}")

            try:
                with self._create_discovery_socket() as sock:
                    # Send probe message
                    self._send_probe(sock)

                    # Wait a bit to let devices respond
                    time.sleep(0.5)

                    # Collect responses
                    responses = self._collect_responses(sock)

                    # Create device objects from responses
                    for resp in responses:
                        addr = resp["address"]
                        if addr not in devices:
                            devices[addr] = ONVIFDevice(
                                address=addr,
                                urls=resp["urls"],
                                types=resp["types"],
                            )

            except Exception as e:
                Logger.error(f"Discovery error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.retries - 1:
                    time.sleep(1)  # Wait before retry
                continue

        # Summarize results
        device_count = len(devices)
        if device_count > 0:
            Logger.success(f"\nDiscovery completed: Found {device_count} device(s)")
            if Logger.DEBUG:
                for device in devices.values():
                    Logger.debug(f"\nDevice details:\n{device}")
        else:
            Logger.warning("\nNo ONVIF devices found on the network")

        return list(devices.values())

    def estimate_discovery_time(self) -> float:
        """Estimate the total time needed for discovery"""
        base_time = self.timeout  # Base timeout
        retry_time = base_time * self.retries  # Time for all retries
        processing_time = 0.5  # Additional processing time
        return base_time + retry_time + processing_time
