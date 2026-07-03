import pytest
import asyncio
from gateway.broker import EventBroker

@pytest.mark.asyncio
async def test_broker_subscribe_publish():
    broker = EventBroker()

    async def consume():
        async for msg in broker.subscribe("1.2.3.4"):
            return msg

    # Start subscriber in background
    task = asyncio.create_task(consume())
    await asyncio.sleep(0.1) # Give it time to subscribe

    # Publish event
    broker.publish("test_event", {"foo": "bar"})

    result = await asyncio.wait_for(task, timeout=1.0)
    assert "event: test_event" in result
    assert '{"foo": "bar"}' in result

@pytest.mark.asyncio
async def test_broker_connection_limit():
    broker = EventBroker()
    broker.MAX_CONNECTIONS_PER_IP = 2

    # Use list to store generators to keep them alive
    subs = []

    # First 2 should succeed
    for _ in range(2):
        gen = broker.subscribe("1.1.1.1")
        # Start the generator by calling __anext__
        asyncio.create_task(gen.__anext__())
        subs.append(gen)

    await asyncio.sleep(0.1)

    # 3rd should fail
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        async for _ in broker.subscribe("1.1.1.1"):
            pass
    assert exc.value.status_code == 429
