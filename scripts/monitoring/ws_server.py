#!/usr/bin/env python3
"""WebSocket server for real-time dashboard updates.

Provides:
- POST /emit: Accept updates from the pipeline.
- GET /ws: WebSocket endpoint for clients to listen to updates.
"""

import asyncio
import json
import logging
import weakref

from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ws_server")

# Use a WeakSet to hold connected websocket clients
connected_clients = weakref.WeakSet()


async def websocket_handler(request):
    """Handle incoming WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    logger.info(f"Client connected. Total clients: {len(connected_clients)}")

    try:
        async for msg in ws:
            # We only expect clients to listen, not to send messages.
            pass
    finally:
        connected_clients.discard(ws)
        logger.info(f"Client disconnected. Total clients: {len(connected_clients)}")

    return ws


async def emit_handler(request):
    """Handle incoming POST events to broadcast."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

    # Broadcast to all connected clients
    message = json.dumps(data)

    if not connected_clients:
        logger.info(f"No clients connected. Dropped message: {message}")
        return web.json_response({"status": "ok", "delivered": 0})

    tasks = []
    for ws in connected_clients:
        if not ws.closed:
            tasks.append(asyncio.create_task(ws.send_str(message)))

    if tasks:
        await asyncio.gather(*tasks)

    logger.info(f"Broadcasted to {len(tasks)} clients: {message}")
    return web.json_response({"status": "ok", "delivered": len(tasks)})


async def health_check(request):
    return web.json_response({"status": "healthy", "clients": len(connected_clients)})


def main():
    app = web.Application()

    # Configure CORS for local development
    import aiohttp_cors
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    cors.add(app.router.add_get("/ws", websocket_handler))
    cors.add(app.router.add_post("/emit", emit_handler))
    cors.add(app.router.add_get("/health", health_check))

    logger.info("Starting WebSocket server on http://0.0.0.0:8080")
    web.run_app(app, host="0.0.0.0", port=8080, access_log=None)


if __name__ == "__main__":
    main()
