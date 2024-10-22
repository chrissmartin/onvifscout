import argparse
import sys
from typing import List, Optional
import urllib3
from colorama import Fore, Style, init

from onvifscout.utils import Logger, print_banner
from onvifscout.discovery import ONVIFDiscovery
from onvifscout.auth import ONVIFAuthProbe
from onvifscout.features import ONVIFFeatureDetector
from onvifscout.help_formatter import ColoredHelpFormatter

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

    # Examples section
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

  {Fore.GREEN}Debug mode:{Style.RESET_ALL}
    onvifscout --debug

{Fore.CYAN}Default Credentials Tested:{Style.RESET_ALL}
  Usernames: admin, root, service
  Passwords: admin, 12345, password
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
            print(f"\n{device}")

        return devices

    except Exception as e:
        Logger.error(f"Discovery failed: {str(e)}")
        if Logger.DEBUG:
            import traceback

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
            import traceback

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
            import traceback

            Logger.debug(traceback.format_exc())


def print_final_results(devices: List[object]) -> None:
    """Print final results for all devices"""
    if not devices:
        return

    Logger.header("Final Results")
    for device in devices:
        print(f"\n{device}")


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

        # Discover devices
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

        # Print final results
        print_final_results(devices)

    except KeyboardInterrupt:
        Logger.warning("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"An unexpected error occurred: {str(e)}")
        if Logger.DEBUG:
            import traceback

            Logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
