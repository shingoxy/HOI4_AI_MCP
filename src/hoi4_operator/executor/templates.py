"""Small, licensed adaptation of HOI4-AI scripted.Planner.find (MIT)."""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image


class Templates:
    def __init__(self, directory: Path):
        self.directory = directory
        self.cache = {}

    def find(self, rgb, name, box=None, threshold=0.90):
        if name not in self.cache:
            path = self.directory / f"{name}.png"
            if not path.is_file():
                return None
            self.cache[name] = np.asarray(Image.open(path).convert("RGB"))
        template = self.cache[name]
        x0, y0, x1, y1 = box or (0, 0, rgb.shape[1], rgb.shape[0])
        crop = rgb[y0:y1, x0:x1]
        h, w = template.shape[:2]
        if crop.shape[0] < h or crop.shape[1] < w or float(template.std()) < 1:
            return None
        scores = cv2.matchTemplate(crop, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, (x, y) = cv2.minMaxLoc(scores)
        if not np.isfinite(score) or score < threshold:
            return None
        return (x0 + x + w // 2, y0 + y + h // 2)
