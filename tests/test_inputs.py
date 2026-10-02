import os
import time

from app.inputs import InputStore


def test_orphan_files_from_a_crash_are_deleted_on_start(tmp_path):
    old = tmp_path / "crashed.jpg"
    old.write_bytes(b"photo")
    os.utime(old, (time.time() - 3600, time.time() - 3600))
    fresh = tmp_path / "other-process.jpg"
    fresh.write_bytes(b"photo")
    InputStore(str(tmp_path))
    assert not old.exists() and fresh.exists()


def test_sweep_forgets_old_inputs_and_their_files(tmp_path):
    inputs = InputStore(str(tmp_path), max_age_seconds=-1)   # everything counts as old
    p = inputs.create("h1", "parent", "photo", b"jpeg", "image/jpeg")
    inputs.sweep()
    assert inputs.get(p.id) is None and list(tmp_path.iterdir()) == []
