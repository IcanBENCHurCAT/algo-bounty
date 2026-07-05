import pytest
import asyncio
from unittest.mock import patch
from gateway.main import lifespan
from fastapi import FastAPI

@pytest.mark.asyncio
async def test_lifespan():
    app = FastAPI()

    with patch("gateway.main.broker.start_cleanup") as mock_cleanup, \
         patch("gateway.main.asyncio.create_task") as mock_create_task, \
         patch("gateway.main.indexer_worker") as mock_worker:

        async with lifespan(app):
            mock_cleanup.assert_called_once()
            mock_create_task.assert_called_once()

            # Since indexer_worker is an async def, mock_worker returns a coroutine.
            # So create_task is called with a coroutine object. We just assert create_task was called.
