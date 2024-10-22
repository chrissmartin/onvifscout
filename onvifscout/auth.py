# auth.py
import concurrent.futures
from itertools import product
from typing import List, Tuple
import time
import xml.etree.ElementTree as ET

import requests
import urllib3
from requests.auth import HTTPDigestAuth

from .models import ONVIFDevice
from .utils import Logger

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ONVIFAuthProbe:
    def __init__(self, max_workers: int = 5, timeout: int = 5, retries: int = 2):
        self.max_workers = max_workers
        self.timeout = timeout
        self.retries = retries
        self._namespaces = {
            "s": "http://www.w3.org/2003/05/soap-envelope",
            "ter": "http://www.onvif.org/ver10/error",
            "tds": "http://www.onvif.org/ver10/device/wsdl",
            "tt": "http://www.onvif.org/ver10/schema",
        }
        self.soap_template = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <GetDeviceInformation xmlns="http://www.onvif.org/ver10/device/wsdl"/>
    </s:Body>
</s:Envelope>"""

    def _verify_response_content(self, response_text: str) -> bool:
        """Verify that the response is a valid ONVIF response"""
        try:
            root = ET.fromstring(response_text)

            # Check for authentication failure indicators
            fault = root.find(".//s:Fault", self._namespaces)
            if fault is not None:
                subcode = fault.find(".//s:Subcode", self._namespaces)
                if subcode is not None and "NotAuthorized" in subcode.text:
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
            device_info = root.find(
                ".//tds:GetDeviceInformationResponse", self._namespaces
            )
            if device_info is not None:
                # Check for required device info fields
                required_fields = [
                    "Manufacturer",
                    "Model",
                    "FirmwareVersion",
                    "SerialNumber",
                ]
                found_fields = [field.tag.split("}")[-1] for field in device_info]
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
        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8",
            "User-Agent": "ONVIF Client 1.0",
        }

        for attempt in range(self.retries):
            try:
                # Try Digest authentication first
                response = requests.post(
                    device_url,
                    auth=HTTPDigestAuth(username, password),
                    data=self.soap_template,
                    headers=headers,
                    timeout=self.timeout,
                    verify=False,
                )

                if response.status_code == 200 and self._verify_response_content(
                    response.text
                ):
                    return True, "Digest"
                elif response.status_code == 401:  # Unauthorized
                    # No need to retry on explicit auth failure
                    break

                # If Digest fails with non-401, try Basic authentication
                if response.status_code != 401:
                    response = requests.post(
                        device_url,
                        auth=(username, password),
                        data=self.soap_template,
                        headers=headers,
                        timeout=self.timeout,
                        verify=False,
                    )

                    if response.status_code == 200 and self._verify_response_content(
                        response.text
                    ):
                        return True, "Basic"
                    elif response.status_code == 401:  # Unauthorized
                        break

                # Add small delay between retries if not explicitly unauthorized
                if attempt < self.retries - 1 and response.status_code != 401:
                    time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                if "401" in str(e):  # Check for 401 in exception message
                    break
                Logger.error(f"Connection error for {device_url}: {str(e)}")
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
