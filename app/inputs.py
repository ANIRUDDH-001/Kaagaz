"""Uploads waiting to be understood. Held in this process's memory and temp dir only:
photos and audio are never written to the database, and are deleted once processed."""
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/heic": ".heic",
              "audio/webm": ".webm", "audio/mp4": ".m4a", "audio/ogg": ".ogg", "audio/mpeg": ".mp3",
              "audio/wav": ".wav", "audio/x-m4a": ".m4a"}

ERRORS = {
    "Gone": "यह काग़ज़ या आवाज़ अब सर्वर पर नहीं है — कृपया फिर से भेजिए।",
    "BadInput": "समझ नहीं आया — कृपया साफ़ फ़ोटो या आवाज़ के साथ फिर से कोशिश करें।",
    "Empty": "कोई आवाज़ सुनाई नहीं दी — फिर से बोलिए।",
    "Busy": "AI अभी व्यस्त है — थोड़ी देर में फिर कोशिश करें।",
}


@dataclass
class PendingInput:
    id: str
    household_id: str
    role: str
    kind: str                 # "photo" | "voice" | "text"
    path: str | None
    mime: str | None
    text: str | None
    status: str = "processing"   # processing -> ready | failed; ready -> confirming -> confirmed
    transcript: str | None = None
    card: dict | None = None
    error: str | None = None
    results: list | None = None  # kept after confirm so a retried confirm returns the same answer
    created: float = field(default_factory=time.monotonic)


class InputStore:
    def __init__(self, upload_dir: str, max_age_seconds: float = 3600, file_max_age_seconds: float = 1800):
        self.dir = Path(upload_dir) if upload_dir else Path(tempfile.gettempdir()) / "kaagaz-uploads"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.max_age = max_age_seconds
        self.file_max_age = file_max_age_seconds   # = PROCESS_TIMEOUT: no live upload is older
        self.items: dict[str, PendingInput] = {}
        self.sweep()   # files left behind by a crashed process

    def create(self, household_id: str, role: str, kind: str, data: bytes | None = None,
               mime: str | None = None, text: str | None = None) -> PendingInput:
        self.sweep()
        input_id = uuid.uuid4().hex
        path = None
        if data is not None:
            ext = EXTENSIONS.get((mime or "").split(";")[0].strip(), ".bin")
            path = str(self.dir / f"{input_id}{ext}")
            Path(path).write_bytes(data)
        p = PendingInput(input_id, household_id, role, kind, path, mime, text)
        self.items[input_id] = p
        return p

    def get(self, input_id: str) -> PendingInput | None:
        return self.items.get(input_id)

    def drop_file(self, p: PendingInput) -> None:
        if p.path:
            Path(p.path).unlink(missing_ok=True)
            p.path = None

    def forget(self, input_id: str) -> None:
        p = self.items.pop(input_id, None)
        if p:
            self.drop_file(p)

    def sweep(self) -> None:
        now = time.monotonic()
        for input_id, p in list(self.items.items()):
            if now - p.created > self.max_age:
                self.forget(input_id)
        # Memory doesn't survive a crash, but files on disk do: delete any upload older than any
        # live one can be, whether or not this process knows about it.
        cutoff = time.time() - self.file_max_age
        for f in self.dir.iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
            except OSError:
                pass
