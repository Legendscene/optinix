import os
import shutil
import subprocess
import time


class DeveloperOptimizer:
    name = "Developer Cleanup"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        deadline = time.time() + 30
        steps = [
            self._clean_npm, self._clean_pip, self._clean_pycache,
            self._clean_git, self._clean_docker, self._clean_ide, self._clean_build_artifacts
        ]
        for step in steps:
            if time.time() > deadline:
                self.results.append({"success": False, "message": "Developer cleanup timed out"})
                break
            try:
                step(deadline)
            except Exception as e:
                self.results.append({"success": False, "message": f"{step.__name__.replace('_clean_', '').replace('_', ' ').title()} failed: {e}"})
        return self.results

    def _walk_bounded(self, root_dir, deadline):
        try:
            for root, dirs, files in os.walk(root_dir):
                if time.time() > deadline:
                    break
                yield root, dirs, files
        except (PermissionError, OSError):
            pass

    def _clean_npm(self, deadline):
        try:
            subprocess.run(["npm", "cache", "clean", "--force"], capture_output=True, timeout=30)
            home = os.path.expanduser("~")
            cleaned = 0
            for root, dirs, _ in self._walk_bounded(home, deadline):
                if "node_modules" in dirs:
                    nm = os.path.join(root, "node_modules")
                    try:
                        shutil.rmtree(nm, ignore_errors=True)
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
                if cleaned >= 20 or time.time() > deadline:
                    break
            self.results.append({"success": True, "message": f"npm cache + {cleaned} node_modules cleaned"})
        except FileNotFoundError:
            self.results.append({"success": True, "message": "npm not found, skipped"})
        except subprocess.TimeoutExpired:
            self.results.append({"success": False, "message": "npm timed out"})

    def _clean_pip(self, deadline):
        try:
            subprocess.run(["pip", "cache", "purge"], capture_output=True, timeout=30)
            self.results.append({"success": True, "message": "pip cache cleaned"})
        except FileNotFoundError:
            self.results.append({"success": True, "message": "pip not found, skipped"})
        except subprocess.TimeoutExpired:
            self.results.append({"success": False, "message": "pip timed out"})

    def _clean_pycache(self, deadline):
        home = os.path.expanduser("~")
        cleaned = 0
        for root, dirs, files in self._walk_bounded(home, deadline):
            for d in dirs[:]:
                if d == "__pycache__":
                    try:
                        shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                        cleaned += 1
                        dirs.remove(d)
                    except (PermissionError, OSError):
                        continue
            for f in files:
                if f.endswith(".pyc"):
                    try:
                        os.remove(os.path.join(root, f))
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
            if cleaned >= 500 or time.time() > deadline:
                break
        self.results.append({"success": True, "message": f"Python cache cleaned ({cleaned} items)"})

    def _clean_git(self, deadline):
        try:
            home = os.path.expanduser("~")
            cleaned = 0
            for root, dirs, _ in self._walk_bounded(home, deadline):
                if ".git" in dirs:
                    try:
                        subprocess.run(["git", "gc", "--auto", "--quiet"],
                                      cwd=root, capture_output=True, timeout=30)
                        cleaned += 1
                    except Exception:
                        pass
                    dirs.remove(".git")
                if cleaned >= 30 or time.time() > deadline:
                    break
            self.results.append({"success": True, "message": f"Git garbage collected ({cleaned} repos)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Git failed: {e}"})

    def _clean_docker(self, deadline):
        try:
            subprocess.run(["docker", "system", "prune", "-f"], capture_output=True, timeout=30)
            self.results.append({"success": True, "message": "Docker system pruned"})
        except FileNotFoundError:
            self.results.append({"success": True, "message": "Docker not found, skipped"})
        except subprocess.TimeoutExpired:
            self.results.append({"success": False, "message": "Docker timed out"})

    def _clean_ide(self, deadline):
        home = os.path.expanduser("~")
        caches = []
        if self.os_type == "windows":
            caches = [
                os.path.join(home, "AppData", "Local", "JetBrains"),
                os.path.join(home, "AppData", "Local", "Microsoft", "VisualStudio"),
                os.path.join(home, "AppData", "Roaming", "Code", "Cache"),
                os.path.join(home, "AppData", "Roaming", "Code", "CachedData"),
                os.path.join(home, ".vscode", "Cache")
            ]
        elif self.os_type == "macos":
            caches = [
                os.path.expanduser("~/Library/Caches/JetBrains"),
                os.path.expanduser("~/Library/Caches/Code"),
                os.path.expanduser("~/Library/Caches/com.apple.Xcode")
            ]
        elif self.os_type == "linux":
            caches = [
                os.path.join(home, ".cache", "JetBrains"),
                os.path.join(home, ".cache", "Code"),
                os.path.join(home, ".cache", "vim")
            ]

        cleaned = 0
        for c in caches:
            if time.time() > deadline:
                break
            if os.path.exists(c):
                try:
                    shutil.rmtree(c, ignore_errors=True)
                    cleaned += 1
                except (PermissionError, OSError):
                    continue
        self.results.append({"success": True, "message": f"IDE caches cleaned ({cleaned} dirs)"})

    def _clean_build_artifacts(self, deadline):
        home = os.path.expanduser("~")
        patterns = ["*.pyc", "*.pyo", "*.o", "*.obj", "*.class"]
        cleaned = 0
        for root, _, files in self._walk_bounded(home, deadline):
            if time.time() > deadline:
                break
            for f in files:
                for pat in patterns:
                    if f.endswith(pat[1:]):
                        try:
                            os.remove(os.path.join(root, f))
                            cleaned += 1
                        except (PermissionError, OSError):
                            pass
            if cleaned >= 500 or time.time() > deadline:
                break
        self.results.append({"success": True, "message": f"Build artifacts cleaned ({cleaned} files)"})
