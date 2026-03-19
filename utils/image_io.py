import cv2
import numpy as np
import os

def imread_safe(file_path: str, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    """
    Safely read an image file handling non-ASCII paths (e.g., Chinese characters).
    
    Args:
        file_path (str): Path to the image file.
        flags (int): Flags for cv2.imdecode (default: cv2.IMREAD_COLOR).
        
    Returns:
        np.ndarray: The image array, or None if reading fails.
    """
    try:
        if not os.path.exists(file_path):
            return None
        return cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), flags)
    except Exception as e:
        print(f"Error reading image {file_path}: {e}")
        return None

def imwrite_safe(file_path: str, img: np.ndarray, params: list = None) -> bool:
    """
    Safely write an image file handling non-ASCII paths (e.g., Chinese characters).
    
    Args:
        file_path (str): Path to save the image.
        img (np.ndarray): Image array to save.
        params (list): Optional parameters for cv2.imencode.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Get directory and extension
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        ext = os.path.splitext(file_path)[1]
        result, n = cv2.imencode(ext, img, params)
        
        if result:
            with open(file_path, mode='wb') as f:
                n.tofile(f)
            return True
        return False
    except Exception as e:
        print(f"Error writing image {file_path}: {e}")
        return False
