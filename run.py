import threading
import time
import webbrowser
import sys

def start_server():
    from app import app, PORT
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)

print("Starting Optinix...")
t = threading.Thread(target=start_server, daemon=True)
t.start()
time.sleep(2)
url = "http://127.0.0.1:5420"
print(f"Opening {url}")
webbrowser.open(url)
print("App running! Close this window to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
    sys.exit(0)
