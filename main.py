import sys
import threading
import os
import webview
from app import app, socketio, PORT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "ui", "assets", "logo.jfif")


def start_server():
    socketio.run(app, host="127.0.0.1", port=PORT, debug=False, allow_unsafe_werkzeug=True)


def main():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    window = webview.create_window(
        title="Optinix - PC Optimizer",
        url=f"http://127.0.0.1:{PORT}",
        width=1200,
        height=750,
        min_size=(900, 600),
        resizable=True,
        frameless=False,
        easy_drag=True,
        background_color="#09090b"
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
