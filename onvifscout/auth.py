import concurrent.futures
import time
import xml.etree.ElementTree as ET
from itertools import product
from typing import List, Tuple

import urllib3

from .models import ONVIFDevice
from .soap import SOAPClient, SOAPMessageBuilder, SOAPParser
from .utils import Logger

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ONVIFAuthProbe:
    def __init__(self, max_workers: int = 5, timeout: int = 5, retries: int = 2):
        self.max_workers = max_workers
        self.timeout = timeout
        self.retries = retries
        self.soap_client = SOAPClient(timeout=timeout, max_retries=retries)

    def _verify_response_content(self, response_text: str) -> bool:
        """Verify that the response is a valid ONVIF response"""
        try:
            root = ET.fromstring(response_text)

            # Check for authentication failure indicators
            fault = SOAPParser.find_all_elements(root, "Fault")
            if fault:
                subcode = SOAPParser.find_all_elements(fault[0], "Subcode")
                if subcode and "NotAuthorized" in subcode[0].text:
                    return False
                return False

            # Check for common error patterns
            if any(
                error in response_text
                for error in [
                    "Sender",
                    "NotAuthorized",
                    "AccessDenied",
                    "AuthenticationFailed",
                    "InvalidArgVal",
                    "NotFound",
                ]
            ):
                return False

            # Verify it's a valid device info response
            device_info = SOAPParser.find_all_elements(
                root, "GetDeviceInformationResponse"
            )
            if device_info:
                # Check for required device info fields
                required_fields = [
                    "Manufacturer",
                    "Model",
                    "FirmwareVersion",
                    "SerialNumber",
                ]
                found_fields = [field.tag.split("}")[-1] for field in device_info[0]]
                return any(field in found_fields for field in required_fields)

            return False

        except ET.ParseError:
            return False
        except Exception as e:
            Logger.error(f"Error verifying response: {str(e)}")
            return False

    def _test_credentials(
        self, device_url: str, username: str, password: str
    ) -> Tuple[bool, str]:
        """Test a single username/password combination with retries"""

        # Create GetDeviceInformation request message
        soap_message = SOAPMessageBuilder.create_get_device_info()

        for attempt in range(self.retries):
            try:
                # Try Digest authentication first
                response = self.soap_client.send_request(
                    device_url, soap_message, (username, password, "Digest")
                )

                if response is not None and self._verify_response_content(
                    ET.tostring(response, encoding="utf-8").decode()
                ):
                    return True, "Digest"

                # If Digest fails, try Basic authentication
                response = self.soap_client.send_request(
                    device_url, soap_message, (username, password, "Basic")
                )

                if response is not None and self._verify_response_content(
                    ET.tostring(response, encoding="utf-8").decode()
                ):
                    return True, "Basic"

                # Add small delay between retries if not explicitly unauthorized
                if attempt < self.retries - 1:
                    time.sleep(0.5)

            except Exception as e:
                Logger.debug(f"Authentication attempt failed: {str(e)}")
                if attempt < self.retries - 1:
                    time.sleep(1)  # Longer delay for connection errors
                continue

        return False, "Invalid credentials"

    def probe_device(
        self, device: ONVIFDevice, usernames: List[str], passwords: List[str]
    ) -> None:
        """Probe device with multiple credential combinations"""
        valid_credentials = []
        total_combinations = len(usernames) * len(passwords)
        completed = 0

        Logger.header(f"Testing credentials for device {device.address}")
        Logger.info(f"Testing {total_combinations} credential combinations...")

        # Deduplicate URLs to avoid redundant testing
        unique_urls = list(set(device.urls))

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_creds = {}
            for url in unique_urls:
                for username, password in product(usernames, passwords):
                    future = executor.submit(
                        self._test_credentials, url, username, password
                    )
                    future_to_creds[future] = (url, username, password)

            for future in concurrent.futures.as_completed(future_to_creds):
                url, username, password = future_to_creds[future]
                completed += 1

                try:
                    success, auth_type = future.result()
                    if success:
                        cred_tuple = (username, password, auth_type)
                        if cred_tuple not in valid_credentials:  # Avoid duplicates
                            valid_credentials.append(cred_tuple)
                            Logger.success(f"\nFound valid credentials for {url}!")
                            Logger.info(f"Username: {username}")
                            Logger.info(f"Password: {password}")
                            Logger.info(f"Auth Type: {auth_type}")

                    Logger.progress(
                        completed, total_combinations, "Testing credentials"
                    )

                except Exception as e:
                    Logger.error(f"\nError testing {username}:{password} - {str(e)}")

        device.valid_credentials = valid_credentials
        print()  # New line after progress bar

    def __del__(self):
        """Cleanup resources"""
        self.soap_client.close()
