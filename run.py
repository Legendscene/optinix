import threading
import time
import webbrowser
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 40)
print("   OPTINIX - PC Optimizer")
print("=" * 40)
print()
print("Starting server...")

from app import app, PORT

def run():
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True)

t = threading.Thread(target=run, daemon=True)
t.start()

for i in range(10):
    time.sleep(0.5)
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
        break
    except:
        continue

url = f"http://127.0.0.1:{PORT}"
print(f"Server ready at {url}")
print("Opening browser...")

webbrowser.open(url)

print()
print("Browser opened! Use sidebar to navigate.")
print("Press Ctrl+C to stop.")
print()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping...")
    sys.exit(0)
