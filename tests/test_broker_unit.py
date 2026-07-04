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

@pytest.mark.asyncio
async def test_broker_connection_tracking_and_cleanup():
    broker = EventBroker()
    
    # Check active counts
    assert broker.get_active_connections("1.1.1.1") == 0
    assert broker.get_total_active_connections() == 0
    
    # Subscribe one connection
    gen = broker.subscribe("1.1.1.1")
    task = asyncio.create_task(gen.__anext__())
    await asyncio.sleep(0.05)
    
    assert broker.get_active_connections("1.1.1.1") == 1
    assert broker.get_total_active_connections() == 1
    
    # Stop connection and clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
        
    await asyncio.sleep(0.05)
    
    # Check cleanup stale
    broker.listeners["stale_ip"] = {"queues": [], "registered_at": 0}
    # Monotonic subtraction should be large
    await broker._cleanup_stale()
    assert "stale_ip" not in broker.listeners
    
    # Start cleanup background task loop
    broker.CLEANUP_INTERVAL_SECONDS = 0.01
    await broker.start_cleanup()
    broker.listeners["stale_ip2"] = {"queues": [], "registered_at": 0}
    await asyncio.sleep(0.05)
    assert "stale_ip2" not in broker.listeners
    
    # Cancel cleanup task to finish nicely
    broker.cleanup_task.cancel()
    try:
        await broker.cleanup_task
    except asyncio.CancelledError:
        pass

