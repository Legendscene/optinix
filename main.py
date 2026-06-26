import sys
import threading
import os
import webview
from app import app, PORT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "ui", "assets", "logo.jfif")


def start_server():
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


def main():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    icon_path = LOGO_PATH if os.path.exists(LOGO_PATH) else None

    window = webview.create_window(
        title="Optinix - PC Optimizer",
        url=f"http://127.0.0.1:{PORT}",
        width=1200,
        height=750,
        min_size=(900, 600),
        resizable=True,
        frameless=False,
        easy_drag=True,
        background_color="#09090b",
        icon=icon_path
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
