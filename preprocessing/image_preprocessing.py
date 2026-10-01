"""
Image Modality Preprocessor
"""

import os
from typing import Tuple, Optional

try:
    from PIL import Image
except ImportError:
    Image = None

def preprocess_image(image_path: str, output_path: str, target_size: Tuple[int, int] = (224, 224)) -> Optional[str]:
    if Image is None:
        raise ImportError("Pillow library is required for image preprocessing.")
    
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "JPEG")
            return output_path
    except Exception as e:
        print(f"Failed to process {image_path}: {e}")
        return None