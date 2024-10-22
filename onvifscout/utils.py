import sys
from datetime import datetime
from colorama import Back, Fore, Style


class Logger:
    DEBUG = False
    _last_progress = ""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════╗
║                ONVIF Scout v0.1.0                 ║
╚══════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.WHITE}A comprehensive ONVIF device discovery and analysis tool{Style.RESET_ALL}
"""

    @staticmethod
    def timestamp() -> str:
        """Return current timestamp for logging"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    @staticmethod
    def set_debug(enabled: bool):
        """Enable or disable debug logging"""
        Logger.DEBUG = enabled
        if enabled:
            Logger.info("Debug logging enabled")

    @staticmethod
    def _print_with_progress_handling(message: str):
        """Print message while properly handling progress bar"""
        # If we previously printed a progress bar, clear it first
        if Logger._last_progress and not message.startswith("\r"):
            sys.stdout.write("\r" + " " * len(Logger._last_progress) + "\r")
            sys.stdout.flush()

        # Print the new message
        print(message)

        # If we had a progress bar, reprint it
        if Logger._last_progress and not message.startswith("\r"):
            sys.stdout.write(Logger._last_progress)
            sys.stdout.flush()

    @staticmethod
    def info(message: str):
        """Log an info message"""
        formatted = (
            f"{Fore.CYAN}[{Logger.timestamp()}] INFO: {message}{Style.RESET_ALL}"
        )
        Logger._print_with_progress_handling(formatted)

    @staticmethod
    def success(message: str):
        """Log a success message"""
        formatted = (
            f"{Fore.GREEN}[{Logger.timestamp()}] SUCCESS: {message}{Style.RESET_ALL}"
        )
        Logger._print_with_progress_handling(formatted)

    @staticmethod
    def warning(message: str):
        """Log a warning message"""
        formatted = (
            f"{Fore.YELLOW}[{Logger.timestamp()}] WARNING: {message}{Style.RESET_ALL}"
        )
        Logger._print_with_progress_handling(formatted)

    @staticmethod
    def error(message: str):
        """Log an error message"""
        formatted = (
            f"{Fore.RED}[{Logger.timestamp()}] ERROR: {message}{Style.RESET_ALL}"
        )
        Logger._print_with_progress_handling(formatted)

    @staticmethod
    def debug(message: str):
        """Log a debug message if debug logging is enabled"""
        if Logger.DEBUG:
            formatted = f"{Fore.MAGENTA}[{Logger.timestamp()}] DEBUG: {message}{Style.RESET_ALL}"
            Logger._print_with_progress_handling(formatted)

    @staticmethod
    def header(message: str):
        """Log a header message"""
        formatted = f"\n{Back.BLUE}{Fore.WHITE}[{Logger.timestamp()}] {message}{Style.RESET_ALL}"
        Logger._print_with_progress_handling(formatted)

    @staticmethod
    def raw(message: str):
        """Print a raw message without timestamp or formatting"""
        Logger._print_with_progress_handling(message)

    @staticmethod
    def progress(current: int, total: int, message: str = "Progress"):
        """Display a progress bar"""
        progress = (current / total) * 100
        bar_length = 30
        filled_length = int(bar_length * current // total)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        progress_message = (
            f"\r{Fore.CYAN}[{Logger.timestamp()}] {message}: |{bar}| "
            f"{progress:.1f}% ({current}/{total}){Style.RESET_ALL}"
        )

        # Store the progress message for handling interleaved logs
        Logger._last_progress = progress_message

        sys.stdout.write(progress_message)
        sys.stdout.flush()

        # Clear the stored progress on completion
        if current == total:
            Logger._last_progress = ""
            sys.stdout.write("\n")
            sys.stdout.flush()

    @staticmethod
    def table(headers: list, rows: list, title: str = None):
        """Display data in a formatted table"""
        # Convert all values to strings and get max widths
        str_rows = [[str(cell) for cell in row] for row in rows]
        widths = [
            max(len(str(header)), max(len(str(row[i])) for row in str_rows))
            for i, header in enumerate(headers)
        ]

        # Create separator line
        separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

        # Print title if provided
        if title:
            Logger.header(title)

        # Print headers
        Logger.raw(separator)
        header_row = (
            "|"
            + "|".join(f" {header:<{width}} " for header, width in zip(headers, widths))
            + "|"
        )
        Logger.raw(header_row)
        Logger.raw(separator)

        # Print rows
        for row in str_rows:
            row_str = (
                "|"
                + "|".join(f" {cell:<{width}} " for cell, width in zip(row, widths))
                + "|"
            )
            Logger.raw(row_str)

        Logger.raw(separator)


def print_banner():
    """Print the application banner"""
    print(Logger.banner)


def format_bytes(size: int) -> str:
    """Format byte size to human readable string"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    minutes = int(seconds / 60)
    seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {int(seconds)}s"
    hours = int(minutes / 60)
    minutes = minutes % 60
    return f"{hours}h {minutes}m {int(seconds)}s"
