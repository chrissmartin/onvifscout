from datetime import datetime
from typing import List, Optional, Tuple


class SnapshotInterface:
    """Interface defining the snapshot capture capabilities"""

    def capture_snapshot(self, device, output_dir: str = "snapshots") -> Optional[str]:
        """Capture a snapshot from the device and save it to the specified directory"""
        raise NotImplementedError

    def verify_ffmpeg(self) -> bool:
        """Verify RTSP capture capabilities"""
        raise NotImplementedError

    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats"""
        raise NotImplementedError

    def get_max_dimensions(self) -> Tuple[int, int]:
        """Get maximum supported image dimensions"""
        raise NotImplementedError

    def estimate_capture_time(self, device_count: int) -> float:
        """Estimate time needed to capture snapshots"""
        # Base estimation logic
        base_time_per_device = 5  # Base processing time
        parallel_factor = max(1, min(device_count, self.max_workers))
        return (device_count * base_time_per_device) / parallel_factor

    def get_snapshot_status(self) -> dict:
        """Get current snapshot capturing status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "supported_formats": self.get_supported_formats(),
            "max_dimensions": self.get_max_dimensions(),
            "rtsp_available": self.verify_ffmpeg(),
            "max_workers": getattr(self, "max_workers", 1),
        }


class AsyncSnapshotInterface(SnapshotInterface):
    """Interface for asynchronous snapshot capture"""

    async def capture_snapshot_async(
        self, device, output_dir: str = "snapshots"
    ) -> Optional[str]:
        """Asynchronously capture a snapshot"""
        raise NotImplementedError

    async def capture_multiple_async(
        self, devices: list, output_dir: str = "snapshots"
    ) -> List[Optional[str]]:
        """Capture snapshots from multiple devices asynchronously"""
        raise NotImplementedError
