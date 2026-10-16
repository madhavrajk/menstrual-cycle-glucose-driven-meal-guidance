"""A teammate's download (folder or zip) should install and load the same way."""

import hashlib
import shutil
import sys
import zipfile

import pytest

from mealguide import paths, setup_data
from mealguide.data.io import read_table
from mealguide.setup_data import REQUIRED


def _fake_download(root):
    folder = root / "mcphases-a-dataset-1.0.0"
    folder.mkdir()
    lines = []
    for name in REQUIRED:
        (folder / name).write_text("id,study_interval,day_in_study\n1,2022,1\n")
        digest = hashlib.sha256((folder / name).read_bytes()).hexdigest()
        lines.append(f"{digest} {name}")  # PhysioNet uses a single space
    (folder / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
    return folder


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "HOME", tmp_path / "mcphases")
    monkeypatch.setattr(paths, "RAW", tmp_path / "mcphases" / "data" / "raw")
    return tmp_path


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["setup_data", *map(str, argv)])
    setup_data.main()


def test_folder_download_installs_as_zip(home, monkeypatch):
    _run(monkeypatch, _fake_download(home))
    assert (paths.RAW / "mcphases-1.0.0.zip").exists()
    assert len(read_table("glucose")) == 1


def test_zip_download_installs(home, monkeypatch):
    folder = _fake_download(home)
    archive = shutil.make_archive(str(home / "download"), "zip", home, folder.name)
    _run(monkeypatch, archive)
    with zipfile.ZipFile(paths.RAW / "mcphases-1.0.0.zip") as z:
        assert any(n.endswith("/glucose.csv") for n in z.namelist())
    assert len(read_table("glucose")) == 1


def test_corrupted_file_is_rejected(home, monkeypatch):
    folder = _fake_download(home)
    (folder / "glucose.csv").write_text("truncated")
    with pytest.raises(SystemExit, match="Checksum failed for: glucose.csv"):
        _run(monkeypatch, folder)


def test_extracted_folder_in_raw_also_loads(home):
    shutil.copytree(_fake_download(home), paths.RAW / "mcphases")
    assert len(read_table("glucose")) == 1


def test_missing_data_gives_setup_hint(home):
    with pytest.raises(FileNotFoundError, match="make data SRC="):
        read_table("glucose")
