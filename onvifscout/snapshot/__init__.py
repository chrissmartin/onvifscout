from .base import ONVIFSnapshotBase
from .capability import CapabilityDetector
from .image import ImageProcessor
from .interface import AsyncSnapshotInterface, SnapshotInterface
from .main import ONVIFSnapshot
from .profile import MediaProfileHandler
from .rtsp import RTSPHandler

__all__ = [
    "ONVIFSnapshot",
    "SnapshotInterface",
    "AsyncSnapshotInterface",
    "ONVIFSnapshotBase",
    "ImageProcessor",
    "RTSPHandler",
    "MediaProfileHandler",
    "CapabilityDetector",
]

# Version of the snapshot module
__version__ = "0.1.0"
