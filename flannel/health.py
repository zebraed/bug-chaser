"""
HTTP health check server for uptime monitoring.
"""
import logging

from aiohttp import web

import discord

logger = logging.getLogger(__name__)


async def start_health_server(bot: "discord.Client", port: int) -> web.AppRunner:
    """Start a lightweight HTTP server that exposes a /health endpoint.

    Returns 200 when the bot is connected and ready, 503 otherwise.

    Args:
        bot: The Discord client instance to check readiness against.
        port: TCP port to listen on.

    Returns:
        The running AppRunner (caller may stop it on shutdown if needed).
    """

    async def health_handler(request: web.Request) -> web.Response:
        if not bot.is_ready():
            return web.Response(status=503, text="starting")
        return web.Response(status=200, text="ok")

    app = web.Application()
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health check server listening on port %d", port)
    return runner
