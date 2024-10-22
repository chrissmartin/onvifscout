from colorama import Fore, Style
import argparse
from typing import Optional, Sequence, Text

from onvifscout.utils import Logger


class ColoredHelpFormatter(argparse.HelpFormatter):
    """Custom formatter for colorful and well-organized help display"""

    def __init__(
        self,
        prog: Text,
        indent_increment: int = 2,
        max_help_position: int = 35,
        width: Optional[int] = None,
    ):
        super().__init__(prog, indent_increment, max_help_position, width)

    def _format_action(self, action: argparse.Action) -> Text:
        if action.option_strings:
            option_strings = ", ".join(
                f"{Fore.GREEN}{opt}{Style.RESET_ALL}" for opt in action.option_strings
            )
            option_part = f"  {option_strings:<35}"
        else:
            option_part = f"  {action.dest:<35}"

        if action.help:
            help_text = self._expand_help(action)
            if action.type is not None:
                type_name = getattr(action.type, "__name__", "value")
                help_text = f"{help_text} {Fore.BLUE}({type_name}){Style.RESET_ALL}"
            return f"{option_part}{Fore.WHITE}{help_text}{Style.RESET_ALL}\n"
        else:
            return f"{option_part}\n"

    def _format_usage(
        self,
        usage: Optional[Text],
        actions: Sequence[argparse.Action],
        groups: Sequence[argparse._ArgumentGroup],
        prefix: Optional[Text],
    ) -> Text:
        if prefix is None:
            prefix = "Usage: "

        return f"""
{Fore.YELLOW}{prefix}{self._prog}{Style.RESET_ALL}

{Fore.WHITE}Optional arguments:{Style.RESET_ALL}
  [-h/--help]              Show this help message
  [--timeout SECS]         Set discovery timeout
  [--debug]                Enable debug output
  [--max-workers NUM]      Set concurrent workers
  [--usernames LIST]       Define usernames to try
  [--passwords LIST]       Define passwords to try
  [--skip-auth]           Skip auth probing
  [--skip-features]       Skip feature detection
  [--no-color]            Disable colored output
  [--quiet]               Minimal output mode

{Logger.banner}"""

    def start_section(self, heading: Optional[Text]):
        heading = f"\n{Fore.CYAN}{heading}{Style.RESET_ALL}" if heading else ""
        return super().start_section(heading)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="",  # Banner is now part of usage
        formatter_class=lambda prog: ColoredHelpFormatter(prog, max_help_position=35),
        add_help=False,
    )

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message",
    )

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
        help="Maximum concurrent authentication attempts",
    )
    auth_group.add_argument(
        "--usernames",
        type=str,
        default="admin,root,service",
        help="Comma-separated list of usernames",
    )
    auth_group.add_argument(
        "--passwords",
        type=str,
        default="admin,12345,password",
        help="Comma-separated list of passwords",
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

    examples = f"""
{Fore.CYAN}Examples:{Style.RESET_ALL}

{Fore.GREEN}Basic scan:{Style.RESET_ALL}
  onvifscout

{Fore.GREEN}Extended scan with more workers:{Style.RESET_ALL}
  onvifscout --timeout 5 --max-workers 10

{Fore.GREEN}Custom credentials:{Style.RESET_ALL}
  onvifscout --usernames admin,root --passwords admin,12345

{Fore.GREEN}Quick discovery only:{Style.RESET_ALL}
  onvifscout --skip-auth --skip-features

{Fore.GREEN}Debug mode:{Style.RESET_ALL}
  onvifscout --debug

{Fore.CYAN}Default Credentials:{Style.RESET_ALL}
  {Fore.WHITE}Usernames:{Style.RESET_ALL} admin, root, service
  {Fore.WHITE}Passwords:{Style.RESET_ALL} admin, 12345, password
"""
    parser.epilog = examples

    return parser
