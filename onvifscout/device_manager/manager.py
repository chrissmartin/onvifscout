import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models import ONVIFCapabilities, ONVIFDevice
from ..utils import Logger


class DeviceManager:
    """Manages ONVIF device information persistence and retrieval"""

    def __init__(self, config_dir: str = None):
        """Initialize device manager with optional custom config directory"""
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".onvifscout"

        self.devices_file = self.config_dir / "devices.json"
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Ensure configuration directory exists"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            Logger.error(f"Failed to create config directory: {str(e)}")
            raise

    def _serialize_capabilities(
        self, capabilities: Optional[ONVIFCapabilities]
    ) -> Optional[Dict]:
        """Convert capabilities object to serializable dictionary"""
        if not capabilities:
            return None

        return {
            "services": list(capabilities.services) if capabilities.services else [],
            "analytics": dict(capabilities.analytics),
            "device": dict(capabilities.device),
            "events": dict(capabilities.events),
            "imaging": dict(capabilities.imaging),
            "media": dict(capabilities.media),
            "ptz": dict(capabilities.ptz),
        }

    def _deserialize_capabilities(self, data: Dict) -> Optional[ONVIFCapabilities]:
        """Convert dictionary to capabilities object"""
        if not data:
            return None

        caps = ONVIFCapabilities()
        caps.services = set(data.get("services", []))
        caps.analytics = data.get("analytics", {})
        caps.device = data.get("device", {})
        caps.events = data.get("events", {})
        caps.imaging = data.get("imaging", {})
        caps.media = data.get("media", {})
        caps.ptz = data.get("ptz", {})
        return caps

    def _serialize_device(
        self,
        device: ONVIFDevice,
        group: str = "default",
        tags: List[str] = None,
        description: str = None,
    ) -> Dict:
        """Convert ONVIFDevice object to serializable dictionary"""
        return {
            "address": device.address,
            "name": device.name,
            "urls": device.urls,
            "types": device.types,
            "valid_credentials": device.valid_credentials,
            "capabilities": self._serialize_capabilities(device.capabilities),
            "last_seen": datetime.now().isoformat(),
            "description": description or getattr(device, "description", ""),
            "tags": tags or getattr(device, "tags", []),
            "group": group or getattr(device, "group", "default"),
        }

    def _deserialize_device(self, data: Dict) -> ONVIFDevice:
        """Convert dictionary to ONVIFDevice object"""
        device = ONVIFDevice(
            address=data["address"],
            urls=data.get("urls", []),
            types=data.get("types", []),
            name=data.get("name"),
            valid_credentials=data.get("valid_credentials", []),
        )
        device.capabilities = self._deserialize_capabilities(data.get("capabilities"))
        device.description = data.get("description", "")
        device.tags = data.get("tags", [])
        device.group = data.get("group", "default")
        device.last_seen = datetime.fromisoformat(
            data.get("last_seen", datetime.now().isoformat())
        )
        return device

    def add_device(
        self,
        device: ONVIFDevice,
        group: str = "default",
        tags: List[str] = None,
        description: str = None,
    ) -> bool:
        """Add or update a device"""
        try:
            devices = self.load_devices()

            # Save device with metadata
            devices[device.address] = self._serialize_device(
                device, group=group, tags=tags, description=description
            )

            # Write to file atomically
            temp_file = self.devices_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(devices, f, indent=2)

            # Atomic replace
            temp_file.replace(self.devices_file)

            Logger.debug(f"Device {device.address} saved successfully")
            return True

        except Exception as e:
            Logger.error(f"Failed to add/update device: {str(e)}")
            return False

    def load_devices(self) -> Dict[str, Dict]:
        """Load all saved devices"""
        try:
            if self.devices_file.exists():
                with open(self.devices_file, "r") as f:
                    return json.load(f)
            return {}
        except json.JSONDecodeError as e:
            Logger.error(f"Failed to parse devices file: {str(e)}")
            return {}
        except Exception as e:
            Logger.error(f"Failed to load devices: {str(e)}")
            return {}

    def get_device(self, address: str) -> Optional[ONVIFDevice]:
        """Get a specific device by address"""
        devices = self.load_devices()
        device_data = devices.get(address)
        if device_data:
            return self._deserialize_device(device_data)
        return None

    def list_devices(
        self, group: str = None, tags: List[str] = None
    ) -> List[ONVIFDevice]:
        """List devices with optional filtering"""
        devices = self.load_devices()
        result = []

        for device_data in devices.values():
            if group and device_data.get("group") != group:
                continue
            if tags and not all(tag in device_data.get("tags", []) for tag in tags):
                continue
            result.append(self._deserialize_device(device_data))

        return sorted(result, key=lambda x: x.address)

    def delete_device(self, address: str) -> bool:
        """Delete a device from storage"""
        try:
            devices = self.load_devices()
            if address not in devices:
                Logger.warning(f"Device {address} not found")
                return False

            del devices[address]

            # Write to file atomically
            temp_file = self.devices_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(devices, f, indent=2)

            # Atomic replace
            temp_file.replace(self.devices_file)

            Logger.debug(f"Device {address} deleted successfully")
            return True

        except Exception as e:
            Logger.error(f"Failed to delete device: {str(e)}")
            return False

    def update_device_metadata(
        self,
        address: str,
        group: str = None,
        tags: List[str] = None,
        description: str = None,
    ) -> bool:
        """Update device metadata"""
        try:
            devices = self.load_devices()
            if address not in devices:
                Logger.error(f"Device {address} not found")
                return False

            device_data = devices[address]
            if group is not None:
                device_data["group"] = group
            if tags is not None:
                device_data["tags"] = tags
            if description is not None:
                device_data["description"] = description

            # Write to file atomically
            temp_file = self.devices_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(devices, f, indent=2)

            # Atomic replace
            temp_file.replace(self.devices_file)

            Logger.debug(f"Device {address} metadata updated successfully")
            return True

        except Exception as e:
            Logger.error(f"Failed to update device metadata: {str(e)}")
            return False

    def get_groups(self) -> List[str]:
        """Get list of all device groups"""
        devices = self.load_devices()
        groups = {device.get("group", "default") for device in devices.values()}
        return sorted(groups)

    def get_all_tags(self) -> List[str]:
        """Get list of all unique tags"""
        devices = self.load_devices()
        tags = set()
        for device in devices.values():
            tags.update(device.get("tags", []))
        return sorted(tags)

    def merge_device_info(self, device: ONVIFDevice) -> None:
        """Merge new device information with existing stored data"""
        try:
            existing = self.get_device(device.address)
            if not existing:
                return

            # Update only if new information is available
            if not device.name and existing.name:
                device.name = existing.name
            if not device.valid_credentials and existing.valid_credentials:
                device.valid_credentials = existing.valid_credentials
            if not device.capabilities and existing.capabilities:
                device.capabilities = existing.capabilities

            # Preserve metadata
            device.description = getattr(existing, "description", "")
            device.tags = getattr(existing, "tags", [])
            device.group = getattr(existing, "group", "default")

        except Exception as e:
            Logger.error(f"Failed to merge device info: {str(e)}")

    def clear_all(self) -> bool:
        """Clear all stored devices"""
        try:
            if self.devices_file.exists():
                self.devices_file.unlink()
            return True
        except Exception as e:
            Logger.error(f"Failed to clear devices: {str(e)}")
            return False
