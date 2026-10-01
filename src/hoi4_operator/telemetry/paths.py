"""Locate HOI4's user log without changing game configuration."""

import ctypes
import os
from pathlib import Path


def default_log_path() -> Path:
    documents = Path.home() / "Documents"
    if os.name == "nt":
        buffer = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
            documents = Path(buffer.value)
    return documents / "Paradox Interactive" / "Hearts of Iron IV" / "logs" / "game.log"
