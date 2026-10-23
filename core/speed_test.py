import os
import urllib.request
import time
import json
import socket
import struct
from typing import Dict

class SpeedTest:
    """Built-in network speed test - measures ping, download, and upload speed."""
    
    def __init__(self):
        self._test_files = [
            "https://speedtests.xyz/1mb.bin",
            "https://speedtests.xyz/5mb.bin",
            "https://speedtests.xyz/10mb.bin",
            "https://speedtests.xyz/25mb.bin",
            "https://speedtests.xyz/50mb.bin",
            "https://speedtests.xyz/100mb.bin",
        ]
        self._sizes = [1, 5, 10, 25, 50, 100]
    
    def test_ping(self, host: str = "8.8.8.8", count: int = 4) -> Dict:
        """Measure ping latency to a host."""
        import subprocess, platform
        param = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            r = subprocess.run(["ping", param, str(count), host], capture_output=True, text=True, timeout=15)
            output = r.stdout
            
            # Parse ping results
            times = []
            for line in output.split("\n"):
                if "time=" in line.lower() or "time<" in line.lower():
                    try:
                        t = line.split("time=")[-1].split("ms")[0].split(" ")[0].strip()
                        if t.startswith("<"):
                            times.append(0.5)
                        else:
                            times.append(float(t))
                    except:
                        pass
            
            avg = sum(times) / len(times) if times else 0
            min_t = min(times) if times else 0
            max_t = max(times) if times else 0
            loss = 0
            if "lost = " in output:
                try:
                    loss_part = output.split("lost = ")[-1].split(",")[0].strip()
                    loss = int(loss_part)
                except:
                    pass
            
            return {
                "host": host,
                "avg_ms": round(avg, 1),
                "min_ms": round(min_t, 1),
                "max_ms": round(max_t, 1),
                "packet_loss": loss,
                "samples": len(times)
            }
        except subprocess.TimeoutExpired:
            return {"host": host, "error": "Ping timed out"}
        except Exception as e:
            return {"host": host, "error": str(e)}
    
    def test_download(self, size_mb: int = 25) -> Dict:
        """Measure download speed by downloading a test file."""
        try:
            # Find closest test file
            idx = min(range(len(self._sizes)), key=lambda i: abs(self._sizes[i] - size_mb))
            url = self._test_files[idx]
            actual_size = self._sizes[idx]
            
            # Measure a real HTTP download; no value is simulated.
            start = time.time()
            req = urllib.request.Request(url, method="GET")
            total = 0
            with urllib.request.urlopen(req, timeout=5) as resp:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    total += len(chunk)
            elapsed = time.time() - start
            
            speed_bps = total * 8 / elapsed if elapsed > 0 else 0
            speed_mbps = speed_bps / 1_000_000
            
            return {
                "ok": True,
                "download_mbps": round(speed_mbps, 2),
                "bytes_downloaded": total,
                "elapsed_seconds": round(elapsed, 2),
                "size_mb": actual_size,
                "timestamp": start,
            }
        except Exception as e:
            # No simulated fallback: a measurement that did not happen must
            # never be reported as a number. ok=False drives the UI's
            # unavailable state instead of showing a fabricated speed.
            return {
                "ok": False,
                "error": f"Download test failed: {e}",
                "size_mb": size_mb,
            }
    
    def test_upload(self, size_mb: int = 5) -> Dict:
        """Measure upload speed by generating and sending data."""
        try:
            # Generate random data
            data = os.urandom(size_mb * 1024 * 1024)
            
            start = time.time()
            req = urllib.request.Request(
                "https://httpbin.org/post",
                data=data,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
            elapsed = time.time() - start
            
            speed_bps = len(data) * 8 / elapsed if elapsed > 0 else 0
            speed_mbps = speed_bps / 1_000_000
            
            return {
                "ok": True,
                "upload_mbps": round(speed_mbps, 2),
                "bytes_uploaded": len(data),
                "elapsed_seconds": round(elapsed, 2),
                "timestamp": start,
            }
        except Exception as e:
            # No simulated fallback (see test_download).
            return {
                "ok": False,
                "error": f"Upload test failed: {e}",
                "size_mb": size_mb,
            }
    
    def test_all(self) -> Dict:
        """Run full speed test (ping + download + upload)."""
        ping = self.test_ping()
        dl = self.test_download(25)
        ul = self.test_upload(5)
        
        return {
            "ping": ping,
            "download": dl,
            "upload": ul,
            "timestamp": time.time()
        }
