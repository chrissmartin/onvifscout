from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from colorama import Fore, Style


@dataclass
class ONVIFCapabilities:
    services: Set[str] = field(default_factory=set)
    analytics: Dict[str, bool] = field(default_factory=dict)
    device: Dict[str, bool] = field(default_factory=dict)
    events: Dict[str, bool] = field(default_factory=dict)
    imaging: Dict[str, bool] = field(default_factory=dict)
    media: Dict[str, bool] = field(default_factory=dict)
    ptz: Dict[str, bool] = field(default_factory=dict)

    def __str__(self) -> str:
        output = []

        if self.services:
            output.append(f"{Fore.CYAN}Supported Services:{Style.RESET_ALL}")
            for service in sorted(self.services):
                output.append(f"  - {Fore.WHITE}{service}{Style.RESET_ALL}")

        categories = {
            "Analytics": self.analytics,
            "Device": self.device,
            "Events": self.events,
            "Imaging": self.imaging,
            "Media": self.media,
            "PTZ": self.ptz,
        }

        for category, capabilities in categories.items():
            if capabilities:
                output.append(f"\n{Fore.CYAN}{category} Capabilities:{Style.RESET_ALL}")
                for cap, supported in capabilities.items():
                    color = Fore.GREEN if supported else Fore.RED
                    symbol = "✓" if supported else "✗"
                    output.append(f"  {color}{symbol}{Style.RESET_ALL} {cap}")

        return "\n".join(output)


@dataclass
class ONVIFDevice:
    address: str
    urls: List[str]
    types: List[str]
    name: Optional[str] = None
    valid_credentials: List[Tuple[str, str, str]] = None
    capabilities: ONVIFCapabilities = None

    def __str__(self) -> str:
        base = f"{Fore.GREEN}Device at {self.address}:{Style.RESET_ALL}\n"
        if self.name:
            base += f"{Fore.CYAN}Name: {Fore.WHITE}{self.name}{Style.RESET_ALL}\n"
        base += f"{Fore.CYAN}URLs:{Style.RESET_ALL}\n"
        base += "\n".join(
            f"  - {Fore.WHITE}{url}{Style.RESET_ALL}" for url in self.urls
        )
        base += f"\n{Fore.CYAN}Types:{Style.RESET_ALL}\n"
        base += "\n".join(
            f"  - {Fore.WHITE}{type_}{Style.RESET_ALL}" for type_ in self.types
        )
        if self.valid_credentials:
            base += f"\n{Fore.GREEN}Valid Credentials:{Style.RESET_ALL}"
            for username, password, auth_type in self.valid_credentials:
                base += f"\n  - {Fore.YELLOW}{username}{Fore.WHITE}:{Fore.YELLOW}{password}{Style.RESET_ALL} ({Fore.CYAN}{auth_type}{Style.RESET_ALL})"
        if self.capabilities:
            base += f"\n\n{self.capabilities}"
        return base
