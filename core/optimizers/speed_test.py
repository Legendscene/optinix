from core.base import OptimizerBase
from core.speed_test import SpeedTest


class SpeedTestOptimizer(OptimizerBase):
    name = "Network Speed & Diagnostics"
    category = "safe"
    admin_required = False
    requirements = {}

    def run(self):
        st = SpeedTest()
        ping = st.test_ping("8.8.8.8", 4)
        dl = st.test_download(25)
        ul = st.test_upload(5)

        if "error" in ping:
            self.add_result(False, f"Ping to {ping.get('host', '8.8.8.8')} failed: {ping['error']}")
        else:
            self.add_result(
                True,
                f"Ping: {ping['avg_ms']}ms avg ({ping['min_ms']}min / {ping['max_ms']}max), {ping['packet_loss']}% loss",
                latency_ms=ping["avg_ms"],
                min_ms=ping["min_ms"],
                max_ms=ping["max_ms"],
                packet_loss=ping["packet_loss"],
            )

        self.add_result(
            True,
            f"Download: {dl['download_mbps']} Mbps ({dl['bytes_downloaded'] / 1024 / 1024:.1f} MB in {dl['elapsed_seconds']}s)",
            download_mbps=dl["download_mbps"],
            bytes_downloaded=dl["bytes_downloaded"],
            elapsed_seconds=dl["elapsed_seconds"],
            simulated=dl.get("simulated", False),
        )

        self.add_result(
            True,
            f"Upload: {ul['upload_mbps']} Mbps ({ul['bytes_uploaded'] / 1024 / 1024:.1f} MB in {ul['elapsed_seconds']}s)",
            upload_mbps=ul["upload_mbps"],
            bytes_uploaded=ul["bytes_uploaded"],
            elapsed_seconds=ul["elapsed_seconds"],
            simulated=ul.get("simulated", False),
        )

        return [r.to_dict() for r in self.results]
