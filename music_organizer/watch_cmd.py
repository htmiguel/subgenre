from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from music_organizer.scan import collect_metadata
from music_organizer.tags import AUDIO_EXTENSIONS

log = logging.getLogger(__name__)


class _AudioHandler(FileSystemEventHandler):
    def __init__(self, debounce_s: float = 2.0) -> None:
        self.debounce_s = debounce_s
        self._lock = threading.Lock()
        self._pending: dict[str, float] = {}
        self._timer: threading.Timer | None = None

    def _schedule(self, path: Path) -> None:
        key = str(path.resolve())
        with self._lock:
            self._pending[key] = time.monotonic()
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_s, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self) -> None:
        with self._lock:
            pending = list(self._pending.keys())
            self._pending.clear()
            self._timer = None
        for key in pending:
            p = Path(key)
            if not p.is_file():
                continue
            if p.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            try:
                collect_metadata(p, features=True)
                log.info("Scanned (metadata + features): %s", p)
            except Exception:
                log.exception("Failed to scan: %s", p)

    def on_created(self, event):  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in AUDIO_EXTENSIONS:
            self._schedule(path)

    def on_moved(self, event):  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if path.suffix.lower() in AUDIO_EXTENSIONS:
            self._schedule(path)


def watch_folder(path: Path, *, debounce_s: float = 2.0) -> None:
    path = path.expanduser().resolve()
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    handler = _AudioHandler(debounce_s=debounce_s)
    observer = Observer()
    observer.schedule(handler, str(path), recursive=True)
    observer.start()
    log.info("Watching %s (recursive); new audio files get scan + features after %.1fs quiet.", path, debounce_s)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
