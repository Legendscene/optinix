import subprocess
import os


class MacOSPlatform:
    name = "macOS"

    def get_launch_agents(self):
        try:
            user_dir = os.path.expanduser("~/Library/LaunchAgents")
            sys_dir = "/System/Library/LaunchAgents"
            return {
                "user": os.listdir(user_dir) if os.path.exists(user_dir) else [],
                "system": os.listdir(sys_dir) if os.path.exists(sys_dir) else []
            }
        except Exception:
            return {"user": [], "system": []}

    def disable_launch_agent(self, agent_name):
        try:
            subprocess.run(
                ["launchctl", "unload", "-w", f"~/Library/LaunchAgents/{agent_name}"],
                capture_output=True, timeout=10
            )
            return True
        except Exception:
            return False
