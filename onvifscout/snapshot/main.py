import concurrent.futures
import os
import shutil
import tempfile
from datetime import datetime
from typing import List, Optional, Tuple

from ..device_contexts import DeviceContextManager
from ..models import ONVIFDevice
from ..utils import Logger
from .base import ONVIFSnapshotBase
from .image import ImageProcessor
from .interface import SnapshotInterface
from .rtsp import RTSPHandler


class ONVIFSnapshot(ONVIFSnapshotBase, SnapshotInterface):
    def __init__(
        self,
        timeout: int = 5,
        max_retries: int = 3,
        image_format: str = "jpg",
        quality: int = 90,
        quiet: bool = False,
        max_workers: int = 5,
    ):
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.max_workers = max_workers
        self.quiet = quiet
        self.image_format = image_format
        self.quality = quality
        self.image_processor = ImageProcessor(image_format, quality)
        self.rtsp_handler = RTSPHandler(timeout, image_processor=self.image_processor)

    def _try_vendor_urls_parallel(
        self, device: ONVIFDevice, context, cred
    ) -> Optional[bytes]:
        """Try vendor-specific snapshot URLs in parallel using device context"""
        headers = {
            "Accept": f"image/{self.image_processor.image_format}, image/*, */*",
            "User-Agent": "ONVIF Client/1.0",
        }

        # Generate URLs from context
        urls = []
        for port in context.ports:
            for path in context.paths:
                url = f"http://{device.address}:{port}{path}"
                if url not in urls:
                    urls.append(url)

        # Try URLs in parallel
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_url = {
                executor.submit(self._try_snapshot_url, url, cred, headers): url
                for url in urls
            }

            try:
                for future in concurrent.futures.as_completed(
                    future_to_url, timeout=10
                ):
                    try:
                        result = future.result()
                        if result:
                            return result
                    except Exception:
                        continue
            except concurrent.futures.TimeoutError:
                Logger.warning("Parallel URL testing timed out")

        return None

    def _ensure_directory(self, directory: str) -> bool:
        """Ensure directory exists and is writable"""
        try:
            os.makedirs(directory, exist_ok=True)
            # Test write permissions by creating a temporary file
            test_file = os.path.join(directory, ".test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                return True
            except (IOError, OSError) as e:
                Logger.error(f"Directory not writable: {directory} - {str(e)}")
                return False
        except Exception as e:
            Logger.error(f"Failed to create directory: {directory} - {str(e)}")
            return False

    def capture_snapshot(
        self, device: ONVIFDevice, output_dir: str = "snapshots"
    ) -> Optional[str]:
        """Capture snapshot using device context for vendor-specific handling"""
        if not device.valid_credentials:
            Logger.error("No valid credentials available")
            return None

        # Ensure output directory exists and is writable
        if not self._ensure_directory(output_dir):
            return None

        cred = device.valid_credentials[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output = os.path.join(
            output_dir, f"snapshot_{device.address}_{timestamp}"
        )

        try:
            context = DeviceContextManager.get_context(device.name)
            Logger.info(f"Using {context.name} device context...")

            # Create a temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Try vendor-specific URLs first
                Logger.info("Trying vendor-specific snapshot URLs...")
                snapshot_data = self._try_vendor_urls_parallel(device, context, cred)
                if snapshot_data:
                    # Process and save to final location
                    return self.image_processor.save_image(snapshot_data, final_output)

                # Try RTSP as fallback
                Logger.info("Attempting RTSP stream capture...")

                for rtsp_url in context.get_rtsp_urls(device.address, cred[0], cred[1]):
                    temp_path = self.rtsp_handler.capture_rtsp_frame(
                        rtsp_url,
                        cred,
                        os.path.join(temp_dir, "rtsp_frame"),
                        self.image_processor.image_format,
                        self.image_processor.quality,
                    )
                    if temp_path and os.path.exists(temp_path):
                        try:
                            # Move the temporary file to final location
                            final_path = f"{final_output}.{self.image_format}"
                            shutil.move(temp_path, final_path)
                            Logger.success(
                                f"Moved snapshot to final location: {final_path}"
                            )
                            return final_path
                        except Exception as e:
                            Logger.error(
                                f"Error moving snapshot to final location: {str(e)}"
                            )
                            continue

                Logger.error("Failed to capture snapshot through any method")
                return None

        except Exception as e:
            Logger.error(f"Error capturing snapshot: {str(e)}")
            return None
        finally:
            self.session.close()

    def verify_ffmpeg(self) -> bool:
        """Verify ffmpeg availability"""
        return self.rtsp_handler.verify_ffmpeg()

    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats"""
        return self.image_processor.get_supported_formats()

    def get_max_dimensions(self) -> Tuple[int, int]:
        """Get maximum supported image dimensions"""
        return self.image_processor.get_max_dimensions()

    def estimate_capture_time(self, device_count: int) -> float:
        """Estimate time needed to capture snapshots"""
        base_time = self.timeout  # Basic operations
        url_test_time = self.timeout * 2  # Maximum time for parallel URL testing
        additional_methods_time = self.timeout * 3  # Time for RTSP and other methods

        # Total time per device
        device_time = base_time + url_test_time + additional_methods_time

        # Account for parallel processing
        parallel_factor = max(1, min(device_count, self.max_workers))
        return (device_count * device_time) / parallel_factor
