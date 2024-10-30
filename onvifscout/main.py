import argparse
import os
import sys
import traceback
from typing import List, Optional

import urllib3
from colorama import Fore, Style, init

from onvifscout.auth import ONVIFAuthProbe
from onvifscout.device_manager.cli import (
    add_device_management_args,
    handle_device_management,
)
from onvifscout.discovery import ONVIFDiscovery
from onvifscout.features import ONVIFFeatureDetector
from onvifscout.help_formatter import ColoredHelpFormatter
from onvifscout.snapshot import ONVIFSnapshot
from onvifscout.utils import Logger, format_duration, print_banner

# Initialize colorama for Windows compatibility
init()

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with enhanced help display"""
    parser = argparse.ArgumentParser(
        formatter_class=ColoredHelpFormatter,
        add_help=False,  # We'll add our own help argument
    )

    # Add custom help argument
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message",
    )

    # Core arguments
    discover_group = parser.add_argument_group("Discovery Options")
    discover_group.add_argument(
        "--timeout", type=int, default=3, help="Discovery timeout in seconds"
    )
    discover_group.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    auth_group = parser.add_argument_group("Authentication Options")
    auth_group.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Maximum number of concurrent authentication attempts",
    )
    auth_group.add_argument(
        "--usernames",
        type=str,
        default="admin,root,service",
        help="Comma-separated list of usernames to try",
    )
    auth_group.add_argument(
        "--passwords",
        type=str,
        default="admin,12345,password",
        help="Comma-separated list of passwords to try",
    )

    feature_group = parser.add_argument_group("Feature Control")
    feature_group.add_argument(
        "--skip-auth", action="store_true", help="Skip authentication probe"
    )
    feature_group.add_argument(
        "--skip-features", action="store_true", help="Skip feature detection"
    )

    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    output_group.add_argument(
        "--quiet", action="store_true", help="Suppress non-essential output"
    )

    # New snapshot options group
    snapshot_group = parser.add_argument_group("Snapshot Options")
    snapshot_group.add_argument(
        "--snapshot",
        action="store_true",
        help="Capture snapshots from discovered devices",
    )
    snapshot_group.add_argument(
        "--snapshot-dir",
        type=str,
        default="snapshots",
        help="Directory to store snapshots (default: snapshots)",
    )
    snapshot_group.add_argument(
        "--snapshot-format",
        type=str,
        choices=["jpg", "jpeg", "png"],
        default="jpg",
        help="Image format for snapshots (default: jpg)",
    )
    snapshot_group.add_argument(
        "--snapshot-quality",
        type=int,
        choices=range(1, 101),
        metavar="[1-100]",
        default=90,
        help="JPEG quality for snapshots, 1-100 (default: 90)",
    )
    snapshot_group.add_argument(
        "--snapshot-timeout",
        type=int,
        default=10,
        help="Timeout for snapshot capture in seconds (default: 10)",
    )
    snapshot_group.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retries for failed snapshot attempts (default: 3)",
    )

    # Add device management arguments
    add_device_management_args(parser)

    # Enhanced examples section
    examples = f"""
    {Fore.CYAN}Examples:{Style.RESET_ALL}
    {Fore.GREEN}Basic scan:{Style.RESET_ALL}
        onvifscout

    {Fore.GREEN}Extended timeout and concurrent processing:{Style.RESET_ALL}
    onvifscout --timeout 5 --max-workers 10

    {Fore.GREEN}Custom credentials:{Style.RESET_ALL}
    onvifscout --usernames admin,root --passwords admin,12345

    {Fore.GREEN}Quick discovery only:{Style.RESET_ALL}
    onvifscout --skip-auth --skip-features

    {Fore.GREEN}Capture snapshots:{Style.RESET_ALL}
    onvifscout --snapshot --snapshot-dir ./captures --snapshot-quality 95

    {Fore.GREEN}Debug mode:{Style.RESET_ALL}
    onvifscout --debug

    {Fore.CYAN}Default Credentials Tested:{Style.RESET_ALL}
    Usernames: admin, root, service
    Passwords: admin, 12345, password

    {Fore.CYAN}Snapshot Support:{Style.RESET_ALL}
    Formats: JPEG (recommended), PNG
    Max Size: Up to 4096x4096 pixels
    Quality: 1-100 (JPEG only, higher is better)
    Storage: Auto-creates snapshot directory if not exists

    {Fore.GREEN}Device Management:{Style.RESET_ALL}
    onvifscout --save-devices --group office --tags "floor1,hallway"
    onvifscout --list-devices
    onvifscout --list-devices --group office
    onvifscout --delete-device 192.168.1.100
    """
    parser.epilog = examples

    return parser


def process_arguments(args: argparse.Namespace) -> None:
    """Process and validate command line arguments"""
    if args.no_color:
        # Disable all colors if --no-color is specified
        init(strip=True)

    if args.debug:
        Logger.set_debug(True)

    if args.quiet:
        # Implement quiet mode logic
        pass

    # Validate numeric arguments
    if args.timeout < 1:
        Logger.error("Timeout must be at least 1 second")
        sys.exit(1)

    if args.max_workers < 1:
        Logger.error("Max workers must be at least 1")
        sys.exit(1)

    # Validate snapshot-related arguments
    if args.snapshot:
        # Check if snapshot directory is valid or can be created
        try:
            os.makedirs(args.snapshot_dir, exist_ok=True)
        except Exception as e:
            Logger.error(f"Invalid snapshot directory: {str(e)}")
            sys.exit(1)

        # Verify write permissions
        if not os.access(args.snapshot_dir, os.W_OK):
            Logger.error("Cannot write to snapshot directory")
            sys.exit(1)

        # Validate snapshot timeout
        if args.snapshot_timeout < 1:
            Logger.error("Snapshot timeout must be at least 1 second")
            sys.exit(1)

        # Validate max retries
        if args.max_retries < 0:
            Logger.error("Max retries cannot be negative")
            sys.exit(1)

        # Validate snapshot quality
        if not 1 <= args.snapshot_quality <= 100:
            Logger.error("Snapshot quality must be between 1 and 100")
            sys.exit(1)


def discover_devices(timeout: int) -> List[Optional[object]]:
    """Discover ONVIF devices on the network"""
    try:
        discoverer = ONVIFDiscovery(timeout=timeout)
        devices = discoverer.discover()

        if not devices:
            Logger.warning("No ONVIF devices found")
            return []

        Logger.success(f"\nFound {len(devices)} ONVIF device(s):")
        for device in devices:
            print(f"Device: \n{device}")

        return devices

    except Exception as e:
        Logger.error(f"Discovery failed: {str(e)}")
        if Logger.DEBUG:
            Logger.debug(traceback.format_exc())
        return []


def probe_authentication(devices: List[object], args: argparse.Namespace) -> None:
    """Probe devices for valid credentials"""
    if not devices:
        return

    usernames = args.usernames.split(",")
    passwords = args.passwords.split(",")

    try:
        prober = ONVIFAuthProbe(max_workers=args.max_workers)
        for device in devices:
            prober.probe_device(device, usernames, passwords)

    except Exception as e:
        Logger.error(f"Authentication probe failed: {str(e)}")
        if Logger.DEBUG:
            Logger.debug(traceback.format_exc())


def detect_features(devices: List[object]) -> None:
    """Detect features for authenticated devices"""
    if not devices:
        return

    try:
        detector = ONVIFFeatureDetector()
        for device in devices:
            if device.valid_credentials:
                detector.detect_features(device)

    except Exception as e:
        Logger.error(f"Feature detection failed: {str(e)}")
        if Logger.DEBUG:
            Logger.debug(traceback.format_exc())


def print_final_results(devices: List[object]) -> None:
    """Print final results for all devices"""
    if not devices:
        return

    Logger.header("Final Results")
    for device in devices:
        print(f"\n{device}")


def process_snapshot_setup(args: argparse.Namespace) -> Optional[ONVIFSnapshot]:
    """Set up and validate snapshot functionality"""
    try:
        # Initialize snapshot tool with all options
        snapshot_tool = ONVIFSnapshot(
            timeout=args.snapshot_timeout,
            max_retries=args.max_retries,
            image_format=args.snapshot_format,
            quality=args.snapshot_quality,
            quiet=args.quiet,
            max_workers=args.max_workers,
        )

        # Get snapshot capabilities and status
        try:
            status = snapshot_tool.get_snapshot_status()

            if not args.quiet:
                Logger.info("\nSnapshot Configuration:")
                Logger.info(f"Format: {args.snapshot_format.upper()}")
                Logger.info(f"Quality: {args.snapshot_quality}")
                Logger.info(f"Output Directory: {args.snapshot_dir}")
                Logger.info(
                    f"Supported Formats: {', '.join(status['supported_formats'])}"
                )
                Logger.info(
                    f"Maximum Image Size: {status['max_dimensions'][0]}x{status['max_dimensions'][1]}"  # noqa: E501
                )

                if status["rtsp_available"]:
                    Logger.success("RTSP capture support is available")
                else:
                    Logger.warning(
                        "RTSP capture support is not available (ffmpeg not found)"
                    )
        except AttributeError:
            # Fallback for backward compatibility
            if not args.quiet:
                Logger.info("\nSnapshot Configuration:")
                Logger.info(f"Format: {args.snapshot_format.upper()}")
                Logger.info(f"Quality: {args.snapshot_quality}")
                Logger.info(f"Output Directory: {args.snapshot_dir}")
                Logger.info("Maximum Image Size: 4096x4096")

                if snapshot_tool.verify_ffmpeg():
                    Logger.success("RTSP capture support is available")
                else:
                    Logger.warning(
                        "RTSP capture support is not available (ffmpeg not found)"
                    )

        return snapshot_tool

    except Exception as e:
        Logger.error(f"Failed to initialize snapshot functionality: {str(e)}")
        if Logger.DEBUG:
            Logger.debug(traceback.format_exc())
        return None


def handle_snapshot_capture(
    snapshot_tool: ONVIFSnapshot, devices: List[object], output_dir: str
) -> None:
    """Handle snapshot capture for multiple devices"""
    if not devices:
        return

    authenticated_devices = [d for d in devices if d.valid_credentials]
    if not authenticated_devices:
        Logger.warning("No devices with valid credentials for snapshot capture")
        return

    # Get estimated time using interface method
    try:
        estimated_time = snapshot_tool.estimate_capture_time(len(authenticated_devices))
        Logger.info(f"\nEstimated capture time: {format_duration(estimated_time)}")
    except Exception as e:
        Logger.debug(f"Could not estimate capture time: {str(e)}")

    capture_results = []
    for device in authenticated_devices:
        Logger.info(f"\nAttempting to capture snapshot from {device.address}")
        try:
            result = snapshot_tool.capture_snapshot(device, output_dir=output_dir)
            if result:
                Logger.success(f"Snapshot saved to: {result}")
                capture_results.append((device.address, result))
            else:
                Logger.warning(f"Failed to capture snapshot from {device.address}")
        except Exception as e:
            Logger.error(f"Error capturing snapshot from {device.address}: {str(e)}")
            if Logger.DEBUG:
                Logger.debug(traceback.format_exc())

    # Print summary
    if capture_results:
        Logger.header("\nSnapshot Capture Summary")
        Logger.success(
            f"Successfully captured {len(capture_results)} of {len(authenticated_devices)} snapshots"  # noqa: E501
        )
        for addr, path in capture_results:
            Logger.info(f"{addr}: {path}")
    else:
        Logger.warning("No snapshots were captured successfully")


def main() -> None:
    """Main entry point for ONVIFScout"""
    try:
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()

        # Process and validate arguments
        process_arguments(args)

        # Show banner unless quiet mode is enabled
        if not args.quiet:
            print_banner()

        # Check if we only need to perform device management operations
        if (args.list_devices or args.delete_device) and not (
            args.save_devices or args.snapshot
        ):
            handle_device_management(args)
            return

        # Discover devices only if needed
        devices = discover_devices(args.timeout)

        # Skip remaining steps if no devices found
        if not devices:
            return

        # Authentication probe
        if not args.skip_auth:
            probe_authentication(devices, args)

            # Feature detection for authenticated devices
            if not args.skip_features:
                detect_features(devices)

        # Handle snapshot capture if requested
        if args.snapshot:
            snapshot_tool = process_snapshot_setup(args)
            if snapshot_tool:
                handle_snapshot_capture(snapshot_tool, devices, args.snapshot_dir)
            else:
                Logger.error(
                    "Snapshot tool initialization failed. Skipping snapshot capture."
                )

        # Handle device management if requested
        if args.save_devices or args.list_devices or args.delete_device:
            handle_device_management(args, devices)

        # Print final results
        print_final_results(devices)

    except KeyboardInterrupt:
        Logger.warning("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"An unexpected error occurred: {str(e)}")
        if Logger.DEBUG:
            Logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
