import os
from typing import Optional

from PIL import Image

from ..utils import Logger


class ImageProcessor:
    def __init__(self, image_format: str = "jpg", quality: int = 90):
        self.image_format = image_format.lower()
        self.quality = quality

    def _is_valid_image(self, data: bytes) -> bool:
        """Validate image data format"""
        return (
            data.startswith(b"\xff\xd8\xff")  # JPEG header
            or data.startswith(b"\x89PNG\r\n\x1a\n")
        )  # PNG header

    def save_image(self, image_data: bytes, output_path: str) -> Optional[str]:
        """Save image data with improved format detection and error handling"""
        temp_path = None
        try:
            # Create a temporary file with original format
            temp_path = output_path + ".temp"
            with open(temp_path, "wb") as f:
                f.write(image_data)

            # Validate image data
            if not self._is_valid_image(image_data):
                Logger.debug(
                    f"Invalid image data received (size: {len(image_data)} bytes)"
                )
                return None

            # Process with PIL
            with Image.open(temp_path) as img:
                Logger.debug(
                    f"Image opened successfully: {img.format} {img.size} {img.mode}"
                )

                # Check and resize if needed
                if img.size[0] > 4096 or img.size[1] > 4096:
                    Logger.warning(
                        f"Image dimensions ({img.size}) exceed 4096x4096, will be resized"  # noqa: E501
                    )
                    img.thumbnail((4096, 4096), Image.Resampling.LANCZOS)

                # Convert mode if needed
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                    Logger.debug(f"Converted image mode from {img.mode} to RGB")

                # Determine format and options
                out_format = self.image_format.upper()
                save_opts = {}

                if out_format in ("JPG", "JPEG"):
                    output_path = os.path.splitext(output_path)[0] + ".jpg"
                    save_opts = {
                        "format": "JPEG",
                        "quality": self.quality,
                        "optimize": True,
                    }
                elif out_format == "PNG":
                    output_path = os.path.splitext(output_path)[0] + ".png"
                    save_opts = {"format": "PNG", "optimize": True}
                else:
                    Logger.error(f"Unsupported image format: {out_format}")
                    return None

                img.save(output_path, **save_opts)
                Logger.success(f"Image saved successfully: {output_path}")
                return output_path

        except Exception as e:
            Logger.error(f"Error processing image: {str(e)}")
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        return None

    def get_supported_formats(self) -> list:
        """Return list of supported image formats"""
        return ["jpg", "jpeg", "png"]

    def get_max_dimensions(self) -> tuple:
        """Return maximum supported image dimensions"""
        return (4096, 4096)
