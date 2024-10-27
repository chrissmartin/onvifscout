import os
import subprocess
from typing import Optional, Tuple
from urllib.parse import urlparse

from onvifscout.snapshot.image import ImageProcessor

from ..utils import Logger


class RTSPHandler:
    def __init__(
        self, timeout: int = 5, image_processor: Optional[ImageProcessor] = None
    ):
        self.timeout = timeout
        self.image_processor = image_processor

    def verify_ffmpeg(self) -> bool:
        """Verify that ffmpeg is available for RTSP capture"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            Logger.warning(
                "ffmpeg not found. RTSP snapshot capture will not be available."
            )
            return False
        except Exception as e:
            Logger.warning(f"Error verifying ffmpeg: {str(e)}")
            return False

    def capture_rtsp_frame(
        self,
        rtsp_url: str,
        auth: Tuple[str, str, str],
        output_path: str,
        image_format: str = "jpg",
        quality: int = 90,
    ) -> Optional[str]:
        """Capture a frame from RTSP stream with enhanced error handling"""
        output_file_path = None
        try:
            output_file_path = f"{output_path}.{image_format}"

            # Add authentication to RTSP URL if not present
            if auth and "@" not in rtsp_url:
                parsed = urlparse(rtsp_url)
                rtsp_url = f"rtsp://{auth[0]}:{auth[1]}@{parsed.hostname}:{parsed.port or 554}{parsed.path}"  # noqa: E501

            # Enhanced ffmpeg command with better options
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-rtsp_transport",  # Use TCP for better reliability
                "tcp",
                "-i",
                rtsp_url,
                "-frames:v",
                "1",
                "-q:v",
                str(min(31, int(31 * (1 - quality / 100)))),
                "-f",
                "image2",
            ]

            # Add format-specific options
            if image_format.lower() in ("jpg", "jpeg"):
                cmd.extend(
                    [
                        "-c:v",
                        "mjpeg",
                        "-huffman",
                        "optimal",  # Better JPEG compression
                        "-qmin",
                        "1",  # Ensure quality bounds
                        "-qmax",
                        "31",
                    ]
                )
            elif image_format.lower() == "png":
                cmd.extend(
                    [
                        "-c:v",
                        "png",
                        "-compression_level",
                        "6",  # Balanced compression
                    ]
                )

            cmd.append(output_file_path)

            Logger.debug(f"Running RTSP capture with command: {' '.join(cmd)}")

            # Run ffmpeg with enhanced error handling
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )

            if process.returncode == 0 and os.path.exists(output_file_path):
                if os.path.getsize(output_file_path) > 0:
                    Logger.success(f"RTSP frame captured: {output_file_path}")
                    return output_file_path
                else:
                    Logger.warning("RTSP capture produced empty file")
                    os.remove(output_file_path)

            else:
                Logger.debug(f"RTSP capture failed: {process.stderr.decode()}")

        except subprocess.TimeoutExpired:
            Logger.warning(f"RTSP capture timed out for URL: {rtsp_url}")
        except Exception as e:
            Logger.debug(f"Error capturing RTSP frame: {str(e)}")

        return None
