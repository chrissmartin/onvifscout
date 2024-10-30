from typing import List

from ..models import ONVIFDevice
from ..utils import Logger
from .manager import DeviceManager


def add_device_management_args(parser) -> None:
    """Add device management arguments to the main parser"""
    device_group = parser.add_argument_group("Device Management")

    device_group.add_argument(
        "--save-devices",
        action="store_true",
        help="Save discovered devices for future reference",
    )

    device_group.add_argument(
        "--list-devices", action="store_true", help="List saved devices"
    )

    device_group.add_argument(
        "--group", type=str, help="Specify device group when saving or filtering"
    )

    device_group.add_argument(
        "--tags", type=str, help="Comma-separated tags for device categorization"
    )

    device_group.add_argument(
        "--description", type=str, help="Add description when saving a device"
    )

    device_group.add_argument(
        "--delete-device",
        type=str,
        metavar="ADDRESS",
        help="Delete a saved device by IP address",
    )


def handle_device_management(
    args, discovered_devices: List[ONVIFDevice] = None
) -> None:
    """Handle device management operations"""
    if not args:
        Logger.error("Invalid arguments provided")
        return
    manager = DeviceManager()

    # Handle operations that don't need discovered devices
    if args.list_devices:
        _list_devices(manager, args.group, args.tags)
        return

    if args.delete_device:
        if manager.delete_device(args.delete_device):
            Logger.success(f"Device {args.delete_device} deleted successfully")
        else:
            Logger.error(f"Failed to delete device {args.delete_device}")
        return

    # Handle operations that need discovered devices
    if args.save_devices:
        if not discovered_devices:
            Logger.error("No devices discovered to save")
            return
        _save_discovered_devices(manager, discovered_devices, args)


def _list_devices(
    manager: DeviceManager, group: str = None, tags_str: str = None
) -> None:
    """List devices with optional filtering"""
    tags = tags_str.split(",") if tags_str and tags_str.strip() else None
    devices = manager.list_devices(group=group, tags=tags)

    if not devices:
        Logger.info("No devices found matching criteria")
        return

    Logger.header("Saved Devices")
    for device in devices:
        print(f"\n{device}")


def _save_discovered_devices(
    manager: DeviceManager, devices: List[ONVIFDevice], args
) -> None:
    """Save discovered devices with metadata"""
    tags = args.tags.split(",") if args.tags else []
    group = args.group or "default"

    for device in devices:
        try:
            if manager.add_device(
                device, group=group, tags=tags, description=args.description or ""
            ):
                Logger.success(f"Saved device {device.address}")
            else:
                Logger.error(f"Failed to save device {device.address}")
        except Exception as e:
            Logger.error(f"Error saving device {device.address}: {str(e)}")
