from dataclasses import dataclass
from typing import List


@dataclass
class DeviceContext:
    name: str  # Vendor name
    ports: List[int]  # Common ports for this vendor
    paths: List[str]  # Snapshot paths for this vendor
    keywords: List[str]  # Keywords to identify this vendor
    auth_modes: List[str]  # Supported auth modes (Basic, Digest)
    media_services: List[str]  # Media service paths

    def matches(self, device_name: str) -> bool:
        """Check if device name matches any vendor keywords"""
        device_name = device_name.lower()
        return any(keyword.lower() in device_name for keyword in self.keywords)


# Device-specific contexts
DEVICE_CONTEXTS = {
    "tp-link": DeviceContext(
        name="TP-Link",
        keywords=["tp-link", "tplink", "vigi"],
        ports=[2020, 80, 8080, 554],
        paths=[
            "/onvif/snapshot",
            "/onvif/media/snapshot",
            "/onvif/media1/snapshot",
            "/onvif/media2/snapshot",
            "/onvif/media3/snapshot",
            "/onvif/media_service/snapshot",
            "/onvif/device_service/snapshot",
            "/onvif/event_service/snapshot",
            "/onvif/snapshot/jpeg",
            "/media/snapshot/stream",
            "/stream/snap",
            "/stream/snapshot",
        ],
        auth_modes=["Digest", "Basic"],
        media_services=[
            "/onvif/media_service",
            "/onvif/device_service",
            "/onvif/service",
        ],
    ),
    "cp-plus": DeviceContext(
        name="CP-Plus",
        keywords=["cp-plus", "cp plus", "cpplus"],
        ports=[80, 8000, 8080, 554],
        paths=[
            "/onvif/media_service/snapshot",
            "/onvif/streaming/channels/1/picture",
            "/onvif/snap.jpg",
            "/picture/1/current",
            "/picture.jpg",
            "/picture/1",
            "/images/snapshot.jpg",
            "/cgi-bin/snapshot.cgi",
            "/cgi-bin/snapshot",
            "/jpeg",
            "/jpg/1/image.jpg",
            "/snap",
        ],
        auth_modes=["Digest", "Basic"],
        media_services=[
            "/onvif/media_service",
            "/onvif/streaming",
            "/media",
        ],
    ),
    "hikvision": DeviceContext(
        name="Hikvision",
        keywords=["hikvision", "hik"],
        ports=[80, 8000, 554],
        paths=[
            "/ISAPI/Streaming/channels/101/picture",
            "/ISAPI/Streaming/channels/1/picture",
            "/Streaming/channels/1/picture",
            "/onvif/snapshot",
            "/onvif-http/snapshot",
        ],
        auth_modes=["Digest", "Basic"],
        media_services=[
            "/ISAPI/Streaming",
            "/onvif/media_service",
        ],
    ),
    "dahua": DeviceContext(
        name="Dahua",
        keywords=["dahua"],
        ports=[80, 8080, 554],
        paths=[
            "/cgi-bin/snapshot.cgi",
            "/cgi-bin/snapshot.cgi?channel=1",
            "/cgi-bin/snapManager.cgi?action=attachFileProc&Flags=1",
            "/snapshot/1",
            "/cgi-bin/snapshot",
        ],
        auth_modes=["Digest", "Basic"],
        media_services=[
            "/onvif/media_service",
            "/cgi-bin",
        ],
    ),
    "generic": DeviceContext(
        name="Generic",
        keywords=[],  # Will be used as fallback
        ports=[80, 8080, 554],
        paths=[
            "/onvif-http/snapshot",
            "/onvif/camera/1/snapshot",
            "/snap.jpg",
            "/snapshot",
            "/image",
            "/image/jpeg.cgi",
            "/cgi-bin/snapshot.cgi",
            "/snapshot.jpg",
            "/jpeg",
            "/video.mjpg",
            "/cgi-bin/api.cgi?cmd=Snap&channel=1",
        ],
        auth_modes=["Digest", "Basic"],
        media_services=[
            "/onvif/media_service",
            "/onvif/device_service",
        ],
    ),
}


class DeviceContextManager:
    @staticmethod
    def get_context(device_name: str) -> DeviceContext:
        """Get the appropriate device context based on device name"""
        if not device_name:
            return DEVICE_CONTEXTS["generic"]

        for context in DEVICE_CONTEXTS.values():
            if context.matches(device_name):
                return context

        return DEVICE_CONTEXTS["generic"]

    @staticmethod
    def get_all_paths(context: DeviceContext) -> List[str]:
        """Get all paths including generic ones"""
        paths = context.paths.copy()
        if context.name.lower() != "generic":
            paths.extend(DEVICE_CONTEXTS["generic"].paths)
        return list(dict.fromkeys(paths))  # Remove duplicates while preserving order
