"""
Web UI Server for Voice OS.
Provides a local web interface for visualization and control.
"""
import json
import logging
import threading
import webbrowser
from pathlib import Path
from flask import Flask, render_template, Response, request, jsonify
from flask_cors import CORS

from .eventbus import get_event_bus, Event

logger = logging.getLogger(__name__)


class WebUIServer:
    """Flask-based web UI server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        """
        Initialize web UI server.

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self.app = Flask(
            __name__,
            template_folder=str(Path(__file__).parent.parent / "webui" / "templates"),
            static_folder=str(Path(__file__).parent.parent / "webui" / "static")
        )
        CORS(self.app)  # Enable CORS for local development
        self.event_bus = get_event_bus()
        self._setup_routes()
        self._server_thread = None

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            """Main UI page."""
            return render_template("index.html")

        @self.app.route("/events")
        def stream():
            """Server-Sent Events endpoint for real-time updates."""
            def event_stream():
                """Generate SSE stream."""
                # Send initial connection message
                yield f"data: {json.dumps({'type': 'connected', 'data': {}})}\n\n"

                # Stream events
                while True:
                    events = self.event_bus.get_events()
                    for event in events:
                        event_data = event.to_dict()
                        yield f"data: {json.dumps(event_data)}\n\n"

                    # Small sleep to prevent busy loop
                    import time
                    time.sleep(0.1)

            return Response(event_stream(), mimetype="text/event-stream")

        @self.app.route("/api/status")
        def status():
            """Get current system status."""
            return jsonify({
                "status": "running",
                "host": self.host,
                "port": self.port
            })

        @self.app.route("/api/confirm", methods=["POST"])
        def confirm():
            """Handle user confirmation from UI."""
            data = request.json
            confirmed = data.get("confirmed", False)

            # Set confirmation result in event bus
            self.event_bus.set_confirmation(confirmed)

            # Also publish event for logging
            self.event_bus.publish("confirmation_result", {
                "confirmed": confirmed
            })

            return jsonify({"success": True})

        @self.app.route("/api/continue", methods=["POST"])
        def continue_recording():
            """Handle user continue from UI."""
            data = request.json
            should_continue = data.get("continue", True)

            # Set continue result in event bus
            self.event_bus.set_continue(should_continue)

            # Also publish event for logging
            self.event_bus.publish("continue_result", {
                "continue": should_continue
            })

            return jsonify({"success": True})

    def start(self, open_browser: bool = True):
        """
        Start the web UI server in a background thread.

        Args:
            open_browser: Whether to auto-open browser
        """
        def run_server():
            # Disable Flask's default logger
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()

        url = f"http://{self.host}:{self.port}"
        logger.info(f"Web UI started at {url}")

        if open_browser:
            # Give server a moment to start
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    def stop(self):
        """Stop the web UI server."""
        # Flask doesn't provide easy shutdown, but daemon thread will exit with main process
        logger.info("Web UI server stopping...")


def create_webui_server(host: str = "127.0.0.1", port: int = 5000) -> WebUIServer:
    """
    Factory function to create web UI server.

    Args:
        host: Server host
        port: Server port

    Returns:
        WebUIServer instance
    """
    return WebUIServer(host=host, port=port)
