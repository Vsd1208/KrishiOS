"""Image preprocessor (resize, EXIF orientation)."""

from pathlib import Path
from loguru import logger
from PIL import Image, ImageOps

class ImagePreprocessor:
    """Preprocesses images for model inference (orientation, resize)."""

    def preprocess(self, image_path: Path, target_size: tuple[int, int] = (224, 224)) -> Path:
        """Preprocesses the image and saves a copy."""
        output_path = image_path.with_suffix(f".preprocessed{image_path.suffix}")
        
        try:
            with Image.open(image_path) as img:
                # 1. Correct EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                # 2. Convert to RGB if needed (handles RGBA/P)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                    
                # 3. Resize (Pad to maintain aspect ratio)
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Create a new image of target_size with black background
                new_img = Image.new("RGB", target_size, (0, 0, 0))
                
                # Paste the resized image into the center
                x = (target_size[0] - img.size[0]) // 2
                y = (target_size[1] - img.size[1]) // 2
                new_img.paste(img, (x, y))
                
                # Save preprocessed version
                # Force JPEG for the preprocessed version for model consistency
                output_path = image_path.with_suffix(".preprocessed.jpg")
                new_img.save(output_path, "JPEG", quality=95)
                
                return output_path
                
        except Exception as e:
            logger.error("ImagePreprocessor: Failed to preprocess image {}: {}", image_path, e)
            # Fallback to original if preprocessing fails (model might still handle it)
            return image_path
