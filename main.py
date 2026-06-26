import sys
import threading
import webview
from app import app, PORT


def start_server():
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


def main():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    window = webview.create_window(
        title="PC Optimizer",
        url=f"http://127.0.0.1:{PORT}",
        width=1200,
        height=750,
        min_size=(900, 600),
        resizable=True,
        frameless=False,
        easy_drag=True,
        background_color="#0a0a0f"
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
