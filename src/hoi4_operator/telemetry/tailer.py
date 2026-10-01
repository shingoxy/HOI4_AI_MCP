"""Read complete new lines from game.log, including after replacement or truncation."""

import os
from pathlib import Path


class LogTailer:
    def __init__(self, path: str | Path, *, start_at_end: bool = True) -> None:
        self.path = Path(path)
        self.start_at_end = start_at_end
        self.generation = 0
        self._identity: tuple[int, int] | None = None
        self._offset = 0
        self._pending = b""
        self._prefix = b""
        self._was_missing = False
        self.last_error: str | None = None

    def poll(self) -> list[str]:
        try:
            with self.path.open("rb") as handle:
                stat = os.fstat(handle.fileno())
                identity = (stat.st_dev, stat.st_ino)
                prefix = handle.read(128)
                changed = (
                    self._identity is not None and (
                        identity != self._identity
                        or stat.st_size < self._offset
                        or not prefix.startswith(self._prefix)
                    )
                )
                if self._identity is None or changed:
                    self.generation += 1
                    self._identity = identity
                    self._offset = (
                        stat.st_size if self.start_at_end and not changed and not self._was_missing
                        else 0
                    )
                    self._pending = b""
                    self._prefix = prefix
                    self._was_missing = False
                else:
                    self._prefix = prefix
                handle.seek(self._offset)
                data = handle.read()
                self._offset = handle.tell()
                self.last_error = None
        except FileNotFoundError:
            # A removed file will be read from the beginning when it reappears.
            self._identity = None
            self._pending = b""
            self._was_missing = True
            self.last_error = "log file missing"
            return []
        except OSError as exc:
            # A transient read failure must not cause old lines to be consumed again.
            self.last_error = str(exc)
            return []
        chunks = (self._pending + data).split(b"\n")
        self._pending = chunks.pop()
        if len(self._pending) > 1024 * 1024:
            self._pending = b""
        return [chunk.rstrip(b"\r").decode("utf-8", errors="replace") for chunk in chunks]
