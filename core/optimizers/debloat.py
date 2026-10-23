from typing import Dict, Any, List
from core.base import OptimizerBase
from core.config import CONFIG
from core.debloater import CustomDebloater


class DebloatOptimizer(OptimizerBase):
    name = "System Debloat Optimizer"
    description = "Disables Windows telemetry, Cortana, OneDrive, Xbox services, and privacy-invading features"
    category = "safe"
    benefit = "Reduces background CPU/RAM usage, improves privacy, and removes unnecessary apps"
    risks = "Xbox services will be disabled. Microsoft may re-enable telemetry via updates."
    admin_required = True
    requirements = {}

    SAFE_CATEGORIES = [
        "windows_telemetry",
        "cortana",
        "onedrive",
        "xbox_gaming",
        "feedback_hub",
        "tips",
        "privacy_general",
    ]

    def run(self) -> List[Dict[str, Any]]:
        debloater = CustomDebloater(CONFIG.os_type)

        for cat_id in self.SAFE_CATEGORIES:
            try:
                result = debloater.apply_category(cat_id)
                cat_name = debloater.debloat_categories[cat_id]["name"]
                if result.get("success"):
                    sub_results = result.get("results", [])
                    success_count = sum(1 for r in sub_results if r.get("success"))
                    total = len(sub_results)
                    self.add_result(
                        True,
                        f"{cat_name}: {success_count}/{total} operations applied",
                        category=cat_id,
                        applied=success_count,
                        total=total,
                    )
                else:
                    self.add_result(
                        False,
                        f"{cat_name}: {result.get('message', 'Unknown error')}",
                        category=cat_id,
                    )
            except Exception as e:
                self.add_result(
                    False,
                    f"{cat_id}: {e}",
                    category=cat_id,
                )

        return [r.to_dict() for r in self.results]
