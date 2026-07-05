import pytest
from unittest.mock import patch, MagicMock
from gateway import main

def test_main_does_not_mount_dashboard():
    with patch("gateway.main.os.path.exists", return_value=False), \
         patch("fastapi.FastAPI.mount") as mock_mount, \
         patch("gateway.main.StaticFiles"):

        # force module reload to trigger top-level mount execution
        import importlib
        importlib.reload(main)

        mock_mount.assert_not_called()
