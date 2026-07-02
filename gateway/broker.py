import asyncio
import json
import time
from typing import Optional, Dict
from fastapi import HTTPException

# SSE Event stream broker
class EventBroker:
    MAX_CONNECTIONS_PER_IP = 10
    STALE_TIMEOUT_SECONDS = 60
    CLEANUP_INTERVAL_SECONDS = 30

    def __init__(self):
        self.listeners: Dict[str, list] = {}  # ip -> [queue, ...]
        self.cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup(self):
        """Start the background cleanup task for stale connections."""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        """Periodically clean up stale entries."""
        while True:
            await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
            await self._cleanup_stale()

    async def _cleanup_stale(self):
        """Remove stale entries where connections have been dead for > 60 seconds."""
        now = time.monotonic()
        stale_ips = []
        for ip, info in list(self.listeners.items()):
            queues = info.get("queues", [])
            registered_at = info.get("registered_at", 0)
            if now - registered_at > self.STALE_TIMEOUT_SECONDS and len(queues) == 0:
                stale_ips.append(ip)
        for ip in stale_ips:
            del self.listeners[ip]

    def get_active_connections(self, ip: str) -> int:
        """Get the number of active connections for an IP."""
        if ip in self.listeners:
            return len(self.listeners[ip].get("queues", []))
        return 0

    def get_total_active_connections(self) -> int:
        """Get total active connections across all IPs."""
        total = 0
        for info in self.listeners.values():
            total += len(info.get("queues", []))
        return total

    async def subscribe(self, ip: str = "unknown"):
        """Subscribe to SSE events with per-IP connection tracking."""
        now = time.monotonic()

        # Initialize tracking for this IP if needed
        if ip not in self.listeners:
            self.listeners[ip] = {"queues": [], "registered_at": now}

        # Check connection limit
        if len(self.listeners[ip]["queues"]) >= self.MAX_CONNECTIONS_PER_IP:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "SSE connection limit reached",
                    "max_connections": self.MAX_CONNECTIONS_PER_IP,
                    "retry_after_seconds": 30
                }
            )

        queue = asyncio.Queue()
        self.listeners[ip]["queues"].append(queue)

        try:
            while True:
                yield await queue.get()
        finally:
            if ip in self.listeners:
                if queue in self.listeners[ip]["queues"]:
                    self.listeners[ip]["queues"].remove(queue)
                if len(self.listeners[ip]["queues"]) == 0:
                    del self.listeners[ip]

    def publish(self, event_type: str, data: dict):
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        for info in self.listeners.values():
            for queue in info.get("queues", []):
                queue.put_nowait(msg)

broker = EventBroker()
