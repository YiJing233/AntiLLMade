from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / 'backend'

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def app_module(monkeypatch, tmp_path):
    import main
    import storage

    db_path = tmp_path / 'test_rss.db'
    monkeypatch.setattr(storage, 'DB_PATH', str(db_path))
    storage.init_db()
    return main


@pytest.fixture()
def client(app_module):
    return TestClient(app_module.app)
