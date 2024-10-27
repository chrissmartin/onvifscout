# device_contexts.py
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DeviceContext:
    name: str  # Vendor name
    keywords: List[str]  # Keywords to identify this vendor
    ports: List[int]  # Common ports for this vendor
    paths: List[str]  # Snapshot paths for this vendor
    auth_modes: List[str]  # Supported auth modes (Basic, Digest)
    media_services: List[str]  # Media service paths
    rtsp_patterns: List[str] = field(default_factory=list)  # RTSP URL patterns
    auth_url_params: Dict[str, List[str]] = field(
        default_factory=dict
    )  # Auth URL parameters patterns
    priority_paths: List[str] = field(
        default_factory=list
    )  # High priority snapshot paths
    stream_ports: List[int] = field(
        default_factory=list
    )  # Streaming ports (RTSP, etc.)

    def matches(self, device_name: str) -> bool:
        """Check if device name matches any vendor keywords"""
        if not device_name:
            return False
        device_name = device_name.lower()
        return any(keyword.lower() in device_name for keyword in self.keywords)

    def get_rtsp_urls(self, address: str, username: str, password: str) -> List[str]:
        """Generate RTSP URLs with credentials"""
        return [
            pattern.format(username=username, password=password, address=address)
            for pattern in self.rtsp_patterns
        ]

    def get_auth_urls(self, base_url: str, username: str, password: str) -> List[str]:
        """Generate URLs with authentication parameters"""
        urls = []
        for auth_type, patterns in self.auth_url_params.items():
            for pattern in patterns:
                urls.append(
                    pattern.format(
                        base_url=base_url, username=username, password=password
                    )
                )
        return urls


# Device-specific contexts with enhanced configurations
DEVICE_CONTEXTS = {
    "tp-link": DeviceContext(
        name="TP-Link",
        keywords=["tp-link", "tplink", "vigi"],
        ports=[2020, 80, 8080, 443],
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
        priority_paths=[
            "/stream/snapshot",
            "/onvif/snapshot",
            "/onvif/media/snapshot",
            "/onvif/media_service/snapshot",
            "/snap.jpg",
            "/snapshot.jpg",
            "/image/jpeg.cgi",
            "/video/mjpg.cgi",
        ],
        auth_modes=["Digest", "Basic"],
        media_services=[
            "/onvif/media_service",
            "/onvif/device_service",
            "/onvif/service",
        ],
        rtsp_patterns=[
            "rtsp://{username}:{password}@{address}:554/stream1",
            "rtsp://{username}:{password}@{address}:554/h264/ch1/main/av_stream",
            "rtsp://{username}:{password}@{address}:554/streaming/channels/1",
        ],
        stream_ports=[554, 8554],
        auth_url_params={
            "digest": [
                "{base_url}/cgi-bin/snapshot.cgi?auth=digest&user={username}&password={password}",
                "{base_url}/cgi-bin/image.cgi?auth=digest&user={username}&password={password}",
            ]
        },
    ),
    "cp-plus": DeviceContext(
        name="CP-Plus",
        keywords=["cp-plus", "cp plus", "cpplus"],
        ports=[80, 8000, 8080, 443],
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
        priority_paths=[
            "/onvif/media_service/snapshot",
            "/cgi-bin/snapshot.cgi",
            "/cgi-bin/jpeg.cgi",
            "/snap.jpg",
            "/snapshot.jpg",
            "/jpeg",
            "/onvif/media/jpeg",
            "/onvif/jpeg",
            "/picture/1/current",
        ],
        auth_modes=["Digest", "Basic"],
        media_services=[
            "/onvif/media_service",
            "/onvif/streaming",
            "/media",
        ],
        rtsp_patterns=[
            "rtsp://{username}:{password}@{address}:554/cam/realmonitor?channel=1&subtype=0",
            "rtsp://{username}:{password}@{address}:554/h264/ch01/main/av_stream",
            "rtsp://{username}:{password}@{address}:554/live/ch1",
        ],
        stream_ports=[554, 8554],
        auth_url_params={
            "digest": [
                "{base_url}/cgi-bin/snapshot.cgi?auth=digest&user={username}&password={password}",
                "{base_url}/cgi-bin/jpeg.cgi?auth=digest&user={username}&password={password}",
            ]
        },
    ),
    "hikvision": DeviceContext(
        name="Hikvision",
        keywords=["hikvision", "hik"],
        ports=[80, 8000, 443],
        paths=[
            "/ISAPI/Streaming/channels/101/picture",
            "/ISAPI/Streaming/channels/1/picture",
            "/Streaming/channels/1/picture",
            "/onvif/snapshot",
            "/onvif-http/snapshot",
        ],
        priority_paths=[
            "/ISAPI/Streaming/channels/101/picture",
            "/ISAPI/Streaming/channels/1/picture",
            "/Streaming/channels/1/picture",
        ],
        auth_modes=["Digest", "Basic"],
        media_services=[
            "/ISAPI/Streaming",
            "/onvif/media_service",
        ],
        rtsp_patterns=[
            "rtsp://{username}:{password}@{address}:554/h264/ch1/main/av_stream",
            "rtsp://{username}:{password}@{address}:554/Streaming/Channels/1",
        ],
        stream_ports=[554, 8554],
        auth_url_params={
            "digest": [
                "{base_url}/ISAPI/Streaming/channels/101/picture?auth=digest&user={username}&password={password}",
            ]
        },
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
        rtsp_patterns=[
            "rtsp://{username}:{password}@{address}:554/live",
            "rtsp://{username}:{password}@{address}:554/stream1",
            "rtsp://{username}:{password}@{address}:554/media",
        ],
        stream_ports=[554],
        auth_url_params={},
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
        paths = []
        # Add priority paths first
        if context.priority_paths:
            paths.extend(context.priority_paths)
        # Add regular paths
        paths.extend(context.paths)
        # Add generic paths if not generic context
        if context.name.lower() != "generic":
            paths.extend(DEVICE_CONTEXTS["generic"].paths)
        return list(dict.fromkeys(paths))  # Remove duplicates while preserving order
