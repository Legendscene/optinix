import os
import shutil
import subprocess


class DeveloperOptimizer:
    name = "Developer Cleanup"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        self._clean_npm()
        self._clean_pip()
        self._clean_pycache()
        self._clean_git()
        self._clean_docker()
        self._clean_ide()
        self._clean_build_artifacts()
        return self.results

    def _clean_npm(self):
        try:
            subprocess.run(["npm", "cache", "clean", "--force"], capture_output=True, timeout=60)
            home = os.path.expanduser("~")
            nm_path = os.path.join(home, "node_modules")
            cleaned = 0
            for root, dirs, files in os.walk(home):
                if "node_modules" in dirs:
                    nm = os.path.join(root, "node_modules")
                    try:
                        shutil.rmtree(nm, ignore_errors=True)
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
                if cleaned >= 20:
                    break
            self.results.append({"success": True, "message": f"npm cache + {cleaned} node_modules cleaned"})
        except FileNotFoundError:
            self.results.append({"success": True, "message": "npm not found, skipped"})
        except Exception as e:
            self.results.append({"success": False, "message": f"npm failed: {e}"})

    def _clean_pip(self):
        try:
            subprocess.run(["pip", "cache", "purge"], capture_output=True, timeout=60)
            self.results.append({"success": True, "message": "pip cache cleaned"})
        except FileNotFoundError:
            self.results.append({"success": True, "message": "pip not found, skipped"})
        except Exception as e:
            self.results.append({"success": False, "message": f"pip failed: {e}"})

    def _clean_pycache(self):
        home = os.path.expanduser("~")
        cleaned = 0
        for root, dirs, files in os.walk(home):
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
            if cleaned >= 500:
                break
        self.results.append({"success": True, "message": f"Python cache cleaned ({cleaned} items)"})

    def _clean_git(self):
        try:
            home = os.path.expanduser("~")
            cleaned = 0
            for root, dirs, files in os.walk(home):
                if ".git" in dirs:
                    try:
                        subprocess.run(["git", "gc", "--auto", "--quiet"],
                                      cwd=root, capture_output=True, timeout=60)
                        cleaned += 1
                    except Exception:
                        pass
                    dirs.remove(".git")
                if cleaned >= 30:
                    break
            self.results.append({"success": True, "message": f"Git garbage collected ({cleaned} repos)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Git failed: {e}"})

    def _clean_docker(self):
        try:
            subprocess.run(["docker", "system", "prune", "-f"], capture_output=True, timeout=120)
            self.results.append({"success": True, "message": "Docker system pruned"})
        except FileNotFoundError:
            self.results.append({"success": True, "message": "Docker not found, skipped"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Docker failed: {e}"})

    def _clean_ide(self):
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
            if os.path.exists(c):
                try:
                    shutil.rmtree(c, ignore_errors=True)
                    cleaned += 1
                except (PermissionError, OSError):
                    continue
        self.results.append({"success": True, "message": f"IDE caches cleaned ({cleaned} dirs)"})

    def _clean_build_artifacts(self):
        home = os.path.expanduser("~")
        patterns = ["*.pyc", "*.pyo", "*.o", "*.obj", "*.class"]
        cleaned = 0
        for root, dirs, files in os.walk(home):
            for f in files:
                for pat in patterns:
                    if f.endswith(pat[1:]):
                        try:
                            os.remove(os.path.join(root, f))
                            cleaned += 1
                        except (PermissionError, OSError):
                            pass
            if cleaned >= 500:
                break
        self.results.append({"success": True, "message": f"Build artifacts cleaned ({cleaned} files)"})
