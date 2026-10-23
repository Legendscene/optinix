import psutil
import ctypes
from core.base import OptimizerBase

SYSTEM_CRITICAL_PREFIXES = [
    "system", "smss", "csrss", "wininit", "services", "lsass",
    "svchost", "winlogon", "fontdrvhost", "sihost", "taskhostw",
    "ctfmon", "explorer"
]

BROWSER_NAMES = {
    "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe",
    "opera.exe", "vivaldi.exe", "tor.exe"
}

GAME_NAMES = {
    "gta5.exe", "gta5", "valorant.exe", "valorant", "cs2.exe", "cs2",
    "fortniteclient-win64-shipping.exe", "fortnite", "minecraft.exe",
    "league of legends.exe", "leagueclient.exe", "riotclientservices.exe",
    "csgo.exe", "dota2.exe", "apex legends.exe", "r5apex.exe",
    "overwatch.exe", "overwatch2.exe", "destiny2.exe", "eldenring.exe",
    "sekiro.exe", "dark souls.exe", "cyberpunk2077.exe",
    "hogwarts legacy.exe", "starfield.exe",
    "call of dutymodernwarfare.exe", "cod.exe", "warzone.exe",
    "pubg.exe", "tslgame.exe", "rainbowsix.exe",
    "rocketleague.exe", "genshinimpact.exe", "honkai.exe",
    "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe",
    "origin.exe", "uplay.exe", "gog galaxy.exe",
    "java.exe"
}

HEAVY_APP_NAMES = {
    "teams.exe", "slack.exe", "discord.exe", "zoom.exe", "skype.exe",
    "spotify.exe", "vlc.exe", "mpv.exe",
    "premiere.exe", "afterfx.exe", "photoshop.exe", "blender.exe",
    "unity.exe", "unreal editor.exe",
    "visual studio code.exe", "code.exe", "pycharm64.exe",
    "intellij idea.exe", "webstorm.exe",
    "docker.exe", "docker desktop.exe"
}


class ProcessOptimizer(OptimizerBase):
    name = "Smart Process Manager"
    description = "Smartly suspends non-essential background processes and frees working sets to reclaim RAM"
    category = "advanced"
    benefit = "Frees RAM from non-essential processes without termination"
    risks = "Some non-essential processes may have slightly longer resume times"
    admin_required = False
    requirements = {}

    def run(self):
        total_scanned = 0
        system_critical_count = 0
        browser_procs = []
        freed_procs = []
        total_freed_mb = 0

        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = proc.info
                pid = info["pid"]
                name = info["name"]
                if not name:
                    continue
                mi = info.get("memory_info")
                rss_mb = round(mi.rss / (1024 * 1024), 1) if mi else 0
                total_scanned += 1
                name_lower = name.lower()

                if any(name_lower.startswith(p) for p in SYSTEM_CRITICAL_PREFIXES):
                    system_critical_count += 1
                    continue

                if name_lower in GAME_NAMES or name in GAME_NAMES:
                    continue

                if name_lower in BROWSER_NAMES or name in BROWSER_NAMES:
                    browser_procs.append({"name": name, "pid": pid, "rss_mb": rss_mb})
                    continue

                if name_lower in HEAVY_APP_NAMES or name in HEAVY_APP_NAMES:
                    handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
                    if handle:
                        ctypes.windll.psapi.EmptyWorkingSet(handle)
                        ctypes.windll.kernel32.CloseHandle(handle)
                        freed_procs.append({"name": name, "pid": pid, "rss_mb": rss_mb})
                        total_freed_mb += rss_mb
                    continue

                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
                if handle:
                    ctypes.windll.psapi.EmptyWorkingSet(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    freed_procs.append({"name": name, "pid": pid, "rss_mb": rss_mb})
                    total_freed_mb += rss_mb

            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                continue

        self.add_result(True, f"Scan complete: {total_scanned} processes scanned", total_scanned=total_scanned)
        self.add_result(True, f"{system_critical_count} system-critical processes (preserved)", system_critical_preserved=system_critical_count)
        if browser_procs:
            self.add_result(True, f"{len(browser_procs)} browser processes detected", browser_processes=browser_procs)
        if freed_procs:
            self.add_result(True, f"Freed working sets of {len(freed_procs)} non-essential processes ({total_freed_mb:.1f} MB)", processes_freed=freed_procs, total_ram_freed_mb=round(total_freed_mb, 1))
        else:
            self.add_result(True, "No non-essential processes to free")

        return [r.to_dict() for r in self.results]
