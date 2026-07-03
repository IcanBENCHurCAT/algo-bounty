from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from ..broker import broker

router = APIRouter(prefix="/api/v1/events", tags=["events"])

@router.get("", summary="Subscribe to events", description="Subscribe to a real-time stream of platform events using Server-Sent Events (SSE). Useful for updating the dashboard in real-time.")
async def event_stream(request: Request):
    """SSE endpoint for real-time marketplace events. Protected against connection flooding."""
    ip = request.client.host if request.client else "unknown"

    async def event_generator():
        async for event in broker.subscribe(ip):
            yield event

    total_active = broker.get_total_active_connections()
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-SSE-Active-Connections": str(total_active)}
    )
