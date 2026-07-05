import pytest
from unittest.mock import patch
from gateway import main

def test_main_mounts_dashboard():
    with patch("gateway.main.os.path.exists", return_value=True), \
         patch("fastapi.FastAPI.mount") as mock_mount, \
         patch("gateway.main.StaticFiles"), \
         patch("gateway.main.broker"), \
         patch("gateway.main.indexer_worker"):
        import importlib
        importlib.reload(main)
        mock_mount.assert_called_once()
