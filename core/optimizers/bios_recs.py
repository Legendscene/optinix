from core.base import OptimizerBase
from core.bios_optimizer import BIOSOptimizer
from core.config import CONFIG


class BIOSRecommendationOptimizer(OptimizerBase):
    name = "BIOS Configuration Guide"
    category = "advanced"
    admin_required = False
    requirements = {}

    def run(self):
        bios = BIOSOptimizer(CONFIG.os_type)
        info = bios.get_bios_info()

        mobo = info["motherboard"]
        manufacturer = mobo.get("manufacturer", "Unknown")
        model = mobo.get("model", "Unknown")
        version = mobo.get("version", "Unknown")

        self.add_result(
            True,
            f"Motherboard: {manufacturer} {model} (rev. {version})",
            manufacturer=manufacturer,
            model=model,
            version=version,
        )

        self.add_result(
            True,
            f"BIOS Vendor: {info['bios_vendor']}",
            bios_vendor=info["bios_vendor"],
        )

        recommendations = bios.get_recommended_settings()
        if recommendations:
            for rec in recommendations:
                self.add_result(
                    True,
                    f"{rec['name']}: {rec['setting']} — {rec['description']}",
                    name=rec["name"],
                    setting=rec["setting"],
                    description=rec["description"],
                )
        else:
            self.add_result(False, "No BIOS recommendations available for this system")

        self.add_result(
            True,
            "BIOS settings are read-only. Apply manually in BIOS/UEFI.",
            read_only=True,
        )

        return [r.to_dict() for r in self.results]
