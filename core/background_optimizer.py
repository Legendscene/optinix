import psutil
import time
import subprocess
import threading


KNOWN_GAMES = [
    "gta5.exe", "gta5", "valorant.exe", "valorant", "cs2.exe", "cs2",
    "fortniteclient-win64-shipping.exe", "fortnite", "minecraft.exe", "java.exe",
    "league of legends.exe", "leagueclient.exe", "riotclientservices.exe",
    "csgo.exe", "dota2.exe", "apex legends.exe", "r5apex.exe",
    "overwatch.exe", "overwatch2.exe", "destiny2.exe",
    "eldenring.exe", "sekiro.exe", "dark souls.exe",
    "cyberpunk2077.exe", "hogwarts legacy.exe", "starfield.exe",
    "call of dutymodernwarfare.exe", "cod.exe", "warzone.exe",
    "pubg.exe", "tslgame.exe", "rainbowsix.exe",
    "rocketleague.exe", "genshinimpact.exe", "honkai.exe",
    "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe",
    "origin.exe", "uplay.exe", "gog galaxy.exe"
]

HEAVY_APPS = {
    "chrome.exe": "browser", "firefox.exe": "browser", "msedge.exe": "browser",
    "brave.exe": "browser", "opera.exe": "browser",
    "teams.exe": "communication", "slack.exe": "communication", "discord.exe": "communication",
    "zoom.exe": "communication", "skype.exe": "communication",
    "spotify.exe": "media", "vlc.exe": "media", "mpv.exe": "media",
    "premiere.exe": "creative", "afterfx.exe": "creative", "photoshop.exe": "creative",
    "blender.exe": "creative", "unity.exe": "creative", "unreal editor.exe": "creative",
    "visual studio code.exe": "dev", "code.exe": "dev", "pycharm64.exe": "dev",
    "intellij idea.exe": "dev", "webstorm.exe": "dev",
    "docker.exe": "dev", "docker desktop.exe": "dev"
}

GAMES_CATEGORY = {
    "competitive": ["valorant.exe", "cs2.exe", "csgo.exe", "fortnite", "apex legends.exe", "r5apex.exe", "overwatch.exe"],
    "open_world": ["gta5.exe", "cyberpunk2077.exe", "eldenring.exe", "starfield.exe", "hogwarts legacy.exe"],
    "esports": ["league of legends.exe", "leagueclient.exe", "dota2.exe", "rocketleague.exe"],
    "casual": ["minecraft.exe", "java.exe", "genshinimpact.exe"]
}


class BackgroundOptimizer:
    def __init__(self, os_type):
        self.os_type = os_type
        self._running = False
        self._thread = None
        self._current_profile = "balanced"
        self._last_scan = 0

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def get_status(self):
        return {
            "running": self._running,
            "current_profile": self._current_profile,
            "detected_apps": self._get_running_apps()
        }

    def _monitor_loop(self):
        while self._running:
            try:
                self._scan_and_optimize()
            except Exception:
                pass
            time.sleep(10)

    def _scan_and_optimize(self):
        now = time.time()
        if now - self._last_scan < 10:
            return
        self._last_scan = now

        apps = self._get_running_apps()
        game_detected = None
        heavy_count = 0

        for app in apps:
            name = app["name"].lower()
            if name in [g.lower() for g in KNOWN_GAMES]:
                game_detected = app
                break
            if name in [a.lower() for a in HEAVY_APPS]:
                heavy_count += 1

        if game_detected:
            profile = self._detect_game_category(game_detected["name"])
            if profile != self._current_profile:
                self._current_profile = profile
                self._apply_profile(profile, game_detected["name"])
        elif heavy_count >= 3:
            if self._current_profile != "productivity":
                self._current_profile = "productivity"
                self._apply_profile("productivity", None)
        else:
            if self._current_profile != "balanced":
                self._current_profile = "balanced"
                self._apply_profile("balanced", None)

    def _detect_game_category(self, game_name):
        name_lower = game_name.lower()
        for cat, games in GAMES_CATEGORY.items():
            for g in games:
                if g.lower() in name_lower or name_lower in g.lower():
                    return cat
        return "gaming"

    def _apply_profile(self, profile, app_name):
        if self.os_type == "windows":
            if profile in ["competitive", "esports"]:
                self._set_performance_mode()
                self._prioritize_foreground()
                self._disable_background_heavy()
            elif profile == "open_world":
                self._set_high_performance()
                self._prioritize_foreground()
            elif profile == "productivity":
                self._set_balanced()
            else:
                self._set_balanced()
        elif self.os_type == "linux":
            if profile in ["competitive", "esports", "open_world"]:
                try:
                    subprocess.run(["sudo", "cpupower", "frequency-set", "-g", "performance"],
                                 capture_output=True, timeout=5)
                except Exception:
                    pass

    def _set_performance_mode(self):
        try:
            cmds = [
                "powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100",
                "powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMINCORES 100",
                "powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PERFBOOSTMODE 2",
                "powercfg /setactive SCHEME_CURRENT"
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=5)
        except Exception:
            pass

    def _set_high_performance(self):
        try:
            subprocess.run(
                ["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    def _set_balanced(self):
        try:
            subprocess.run(
                ["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    def _prioritize_foreground(self):
        try:
            subprocess.run(
                ["reg", "add",
                 "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile",
                 "/v", "SystemResponsiveness", "/t", "REG_DWORD", "/d", "0", "/f"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    def _disable_background_heavy(self):
        try:
            heavy = ["Teams", "Slack", "OneDrive", "Spotify"]
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] in heavy:
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

    def _get_running_apps(self):
        apps = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                name = info.get('name', '')
                if name:
                    apps.append({
                        "name": name,
                        "pid": info.get('pid', 0),
                        "cpu": info.get('cpu_percent', 0),
                        "memory": info.get('memory_percent', 0)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return apps
