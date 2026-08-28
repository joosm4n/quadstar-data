import tifffile as tf
from pathlib import Path
import numpy as np
from typing import Any


def get_tiff_stats(image_path: Path) -> dict[str, np.floating[Any]]:
    image = tf.imread(image_path.absolute()).flatten()
    stats: dict[str, np.floating[Any]] = {}

    stats["median"] = np.median(image)
    stats["mean"] = np.mean(image)
    stats["std"] = np.std(image)
    stats["var"] = np.var(image)
    stats["max"] = np.max(image)
    stats["min"] = np.min(image)

    return stats
