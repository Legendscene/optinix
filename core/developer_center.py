import os
import subprocess
import shutil
import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from core.config import CONFIG
from core.logger import get_logger
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_SAFE

logger = get_logger(__name__)


class DevEnvironmentChecker:
    def check_all(self) -> Dict[str, Any]:
        return {
            "python": self.check_python(),
            "node": self.check_node(),
            "git": self.check_git(),
            "java": self.check_java(),
            "docker": self.check_docker(),
            "winget": self.check_winget(),
            "chocolatey": self.check_chocolatey(),
            "scoop": self.check_scoop(),
            "dotnet": self.check_dotnet(),
            "rust": self.check_rust(),
            "go": self.check_go(),
            "vscode": self.check_vscode(),
            "cmake": self.check_cmake(),
            "msbuild": self.check_msbuild(),
            "android_sdk": self.check_android_sdk(),
        }

    def _run_version(self, cmd: List[str]) -> Optional[str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return r.stdout.strip() or r.stderr.strip() or None
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

    def _run_json(self, cmd: List[str]) -> Optional[Any]:
        out = self._run_version(cmd)
        if out:
            try:
                return json.loads(out)
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    def check_python(self) -> Dict[str, Any]:
        ver = self._run_version(["python", "--version"])
        pip_ver = self._run_version(["pip", "--version"])
        venv = self._run_version(["python", "-m", "venv", "--help"])
        path = None
        try:
            r = subprocess.run(["where" if CONFIG.os_type == "windows" else "which", "python"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                path = r.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return {
            "installed": ver is not None,
            "version": ver.split()[-1] if ver else None,
            "path": path,
            "pip_version": pip_ver.split()[-1] if pip_ver else None,
            "venv_available": venv is not None,
        }

    def check_node(self) -> Dict[str, Any]:
        ver = self._run_version(["node", "--version"])
        npm_ver = self._run_version(["npm", "--version"])
        npx = self._run_version(["npx", "--version"])
        return {
            "installed": ver is not None,
            "version": ver.lstrip("v") if ver else None,
            "npm_version": npm_ver,
            "npx_available": npx is not None,
        }

    def check_git(self) -> Dict[str, Any]:
        ver = self._run_version(["git", "--version"])
        config_present = False
        if ver:
            user = self._run_version(["git", "config", "--global", "user.name"])
            email = self._run_version(["git", "config", "--global", "user.email"])
            config_present = bool(user and email)
        return {
            "installed": ver is not None,
            "version": ver.replace("git version ", "") if ver else None,
            "config_present": config_present,
        }

    def check_java(self) -> Dict[str, Any]:
        ver = self._run_version(["java", "-version"])
        jdk = self._run_version(["javac", "-version"])
        parsed_ver = None
        if ver:
            m = re.search(r'(\d+\.\d+\.\d+[_\d]*)', ver)
            if m:
                parsed_ver = m.group(1)
        jre_path = None
        if CONFIG.os_type == "windows":
            jre_path = os.environ.get("JAVA_HOME")
        elif CONFIG.os_type in ("linux", "macos"):
            jre_path = self._run_version(["which", "java"])
        return {
            "installed": ver is not None,
            "version": parsed_ver,
            "jre": ver is not None,
            "jdk": jdk is not None,
            "jdk_version": jdk.replace("javac ", "") if jdk else None,
            "java_home": jre_path,
        }

    def check_docker(self) -> Dict[str, Any]:
        ver = self._run_version(["docker", "--version"])
        daemon_running = False
        images = 0
        containers = 0
        if ver:
            info = self._run_json(["docker", "info", "--format", "{{json .}}"])
            if info:
                daemon_running = True
                images = len(self._run_json(["docker", "images", "-q"]) or [])
                cont_list = self._run_json(["docker", "ps", "-a", "-q"])
                containers = len(cont_list) if isinstance(cont_list, list) else 0
        return {
            "installed": ver is not None,
            "version": ver.replace("Docker version ", "").split(",")[0] if ver else None,
            "daemon_running": daemon_running,
            "images": images,
            "containers": containers,
        }

    def check_winget(self) -> Dict[str, Any]:
        ver = self._run_version(["winget", "--version"])
        pkgs = None
        if ver:
            r = subprocess.run(["winget", "list", "--accept-source-agreements"],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                pkgs = sum(1 for line in r.stdout.split("\n") if line.strip() and not line.startswith(" "))
        return {
            "installed": ver is not None,
            "version": ver,
            "packages_available": pkgs or 0,
        }

    def check_chocolatey(self) -> Dict[str, Any]:
        ver = self._run_version(["choco", "--version"])
        return {
            "installed": ver is not None,
            "version": ver,
        }

    def check_scoop(self) -> Dict[str, Any]:
        ver = self._run_version(["scoop", "--version"])
        buckets = 0
        if ver:
            out = self._run_version(["scoop", "bucket", "list"])
            if out:
                buckets = len([l for l in out.split("\n") if l.strip()])
        return {
            "installed": ver is not None,
            "version": ver,
            "bucket_count": buckets,
        }

    def check_dotnet(self) -> Dict[str, Any]:
        ver = self._run_version(["dotnet", "--version"])
        runtimes = []
        out = self._run_version(["dotnet", "--list-runtimes"])
        if out:
            runtimes = [l.strip() for l in out.split("\n") if l.strip()]
        return {
            "installed": ver is not None,
            "version": ver,
            "runtimes": runtimes,
        }

    def check_rust(self) -> Dict[str, Any]:
        rustc = self._run_version(["rustc", "--version"])
        cargo = self._run_version(["cargo", "--version"])
        return {
            "installed": rustc is not None,
            "rustc_version": rustc.replace("rustc ", "") if rustc else None,
            "cargo_version": cargo.replace("cargo ", "") if cargo else None,
        }

    def check_go(self) -> Dict[str, Any]:
        ver = self._run_version(["go", "version"])
        gopath = os.environ.get("GOPATH") or os.path.join(os.path.expanduser("~"), "go")
        return {
            "installed": ver is not None,
            "version": ver.replace("go version ", "") if ver else None,
            "gopath": gopath if os.path.isdir(gopath) else None,
        }

    def check_vscode(self) -> Dict[str, Any]:
        code_cmd = "code"
        if CONFIG.os_type == "windows":
            code_cmd = "code.cmd"
        ver = self._run_version([code_cmd, "--version"])
        extensions = []
        ext_count = 0
        if ver:
            lines = ver.split("\n")
            actual_ver = lines[0].strip() if lines else None
            ext_out = self._run_version([code_cmd, "--list-extensions"])
            if ext_out:
                extensions = [e.strip() for e in ext_out.split("\n") if e.strip()]
                ext_count = len(extensions)
        else:
            actual_ver = None
            common_paths = [
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "bin", "code.cmd"),
                "/usr/local/bin/code",
                "/usr/bin/code",
            ]
            for p in common_paths:
                if os.path.exists(p):
                    actual_ver = "installed"
                    break
        return {
            "installed": actual_ver is not None,
            "version": actual_ver,
            "extensions_count": ext_count,
            "extensions": extensions,
        }

    def check_cmake(self) -> Dict[str, Any]:
        ver = self._run_version(["cmake", "--version"])
        parsed = None
        if ver:
            for line in ver.split("\n"):
                m = re.search(r'cmake\s+version\s+([\d.]+)', line)
                if m:
                    parsed = m.group(1)
                    break
        return {
            "installed": ver is not None,
            "version": parsed,
        }

    def check_msbuild(self) -> Dict[str, Any]:
        msbuild_paths = [
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
        ]
        ver = None
        vs_version = None
        for path in msbuild_paths:
            if os.path.exists(path):
                r = subprocess.run([path, "/version"], capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    ver = r.stdout.strip().split("\n")[0] if r.stdout else None
                if "2022" in path:
                    vs_version = "2022"
                elif "2019" in path:
                    vs_version = "2019"
                break
        return {
            "installed": ver is not None or any(os.path.exists(p) for p in msbuild_paths),
            "version": ver,
            "vs_version": vs_version,
        }

    def check_android_sdk(self) -> Dict[str, Any]:
        sdk_path = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or ""
        result = {
            "installed": bool(sdk_path) and os.path.isdir(sdk_path),
            "path": sdk_path if os.path.isdir(sdk_path) else None,
            "platform_tools": False,
            "build_tools": [],
            "platforms": [],
        }
        if result["installed"]:
            pt = os.path.join(sdk_path, "platform-tools")
            result["platform_tools"] = os.path.isdir(pt)
            bt_dir = os.path.join(sdk_path, "build-tools")
            if os.path.isdir(bt_dir):
                result["build_tools"] = [d for d in os.listdir(bt_dir)
                                          if os.path.isdir(os.path.join(bt_dir, d))]
            plat_dir = os.path.join(sdk_path, "platforms")
            if os.path.isdir(plat_dir):
                result["platforms"] = [d for d in os.listdir(plat_dir)
                                        if os.path.isdir(os.path.join(plat_dir, d))]
        return result


class PackageManager:
    # Column titles seen in the tabular output of the supported managers; a row
    # made only of these is a header, not a package.
    _LIST_HEADERS = {
        "name", "id", "version", "available", "source", "latest", "type",
        "package", "commands", "tools", "status", "description", "installed",
        "publisher", "notes", "upgrade", "",
    }

    @staticmethod
    def _run(cmd: List[str], timeout: int = 60) -> Tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout, r.stderr
        except FileNotFoundError:
            return -1, "", f"{cmd[0]} not found"
        except subprocess.TimeoutExpired:
            return -2, "", "Command timed out"
        except Exception as e:
            return -3, "", str(e)

    @staticmethod
    def install_package(manager: str, package_name: str) -> Dict[str, Any]:
        manager = manager.lower().strip()
        cmd = None
        if manager == "winget":
            cmd = ["winget", "install", "--accept-source-agreements", "--accept-package-agreements", package_name]
        elif manager == "chocolatey":
            cmd = ["choco", "install", "-y", package_name]
        elif manager == "scoop":
            cmd = ["scoop", "install", package_name]
        elif manager == "npm":
            cmd = ["npm", "install", "-g", package_name]
        elif manager == "pip":
            cmd = ["pip", "install", package_name]
        elif manager == "dotnet":
            cmd = ["dotnet", "tool", "install", "-g", package_name]
        else:
            return {"success": False, "error": f"Unsupported package manager: {manager}"}
        code, stdout, stderr = PackageManager._run(cmd)
        return {
            "success": code == 0,
            "manager": manager,
            "package": package_name,
            "stdout": stdout,
            "stderr": stderr,
            "error": stderr if code != 0 else None,
        }

    @staticmethod
    def update_package(manager: str, package_name: str) -> Dict[str, Any]:
        manager = manager.lower().strip()
        cmd = None
        if manager == "winget":
            cmd = ["winget", "upgrade", "--accept-source-agreements", "--accept-package-agreements", package_name]
        elif manager == "chocolatey":
            cmd = ["choco", "upgrade", "-y", package_name]
        elif manager == "scoop":
            cmd = ["scoop", "update", package_name]
        elif manager == "npm":
            cmd = ["npm", "update", "-g", package_name]
        elif manager == "pip":
            cmd = ["pip", "install", "--upgrade", package_name]
        elif manager == "dotnet":
            cmd = ["dotnet", "tool", "update", "-g", package_name]
        else:
            return {"success": False, "error": f"Unsupported package manager: {manager}"}
        code, stdout, stderr = PackageManager._run(cmd)
        return {
            "success": code == 0,
            "manager": manager,
            "package": package_name,
            "stdout": stdout,
            "stderr": stderr,
            "error": stderr if code != 0 else None,
        }

    @staticmethod
    def remove_package(manager: str, package_name: str) -> Dict[str, Any]:
        manager = manager.lower().strip()
        cmd = None
        if manager == "winget":
            cmd = ["winget", "uninstall", "--accept-source-agreements", package_name]
        elif manager == "chocolatey":
            cmd = ["choco", "uninstall", "-y", package_name]
        elif manager == "scoop":
            cmd = ["scoop", "uninstall", package_name]
        elif manager == "npm":
            cmd = ["npm", "uninstall", "-g", package_name]
        elif manager == "pip":
            cmd = ["pip", "uninstall", "-y", package_name]
        elif manager == "dotnet":
            cmd = ["dotnet", "tool", "uninstall", "-g", package_name]
        else:
            return {"success": False, "error": f"Unsupported package manager: {manager}"}
        code, stdout, stderr = PackageManager._run(cmd)
        return {
            "success": code == 0,
            "manager": manager,
            "package": package_name,
            "stdout": stdout,
            "stderr": stderr,
            "error": stderr if code != 0 else None,
        }

    @staticmethod
    def search_packages(manager: str, query: str) -> List[Dict[str, Any]]:
        manager = manager.lower().strip()
        cmd = None
        if manager == "winget":
            cmd = ["winget", "search", "--accept-source-agreements", query]
        elif manager == "chocolatey":
            cmd = ["choco", "search", query]
        elif manager == "scoop":
            cmd = ["scoop", "search", query]
        elif manager == "npm":
            cmd = ["npm", "search", query]
        elif manager == "pip":
            cmd = ["pip", "search", query]
        elif manager == "dotnet":
            cmd = ["dotnet", "tool", "search", query]
        else:
            return [{"error": f"Unsupported package manager: {manager}"}]
        code, stdout, stderr = PackageManager._run(cmd)
        results = []
        if code == 0 and stdout:
            for line in stdout.split("\n"):
                line = line.strip()
                if line and not line.startswith("Name") and not line.startswith("---"):
                    parts = line.split()
                    if parts:
                        results.append({
                            "name": parts[0],
                            "source": manager,
                            "raw": line,
                        })
        return results

    @staticmethod
    def list_installed(manager: str) -> List[Dict[str, Any]]:
        manager = manager.lower().strip()
        cmd = None
        if manager == "winget":
            cmd = ["winget", "list", "--accept-source-agreements"]
        elif manager == "chocolatey":
            cmd = ["choco", "list", "-lo"]
        elif manager == "scoop":
            cmd = ["scoop", "list"]
        elif manager == "npm":
            cmd = ["npm", "list", "-g", "--depth=0"]
        elif manager == "pip":
            cmd = ["pip", "list", "--format=json"]
        elif manager == "dotnet":
            cmd = ["dotnet", "tool", "list", "-g"]
        else:
            # An unknown manager is reported by the caller, not as a fake
            # package row inside the list.
            return []
        code, stdout, stderr = PackageManager._run(cmd)
        packages = []
        header_cols = None
        if code == 0 and stdout:
            if manager == "pip":
                try:
                    return json.loads(stdout)
                except json.JSONDecodeError:
                    pass
            for line in stdout.split("\n"):
                line = line.strip()
                if not line or line.startswith("---"):
                    continue
                if manager == "npm":
                    # `npm list -g` prints a tree: "└── pkg@1.2.3"
                    line = line.lstrip("`+-| ").strip()
                    if not line or "@" not in line:
                        continue
                    name, _, version = line.partition("@")
                    packages.append({"name": name, "version": version})
                    continue
                # The tabular managers print warnings on stdout, e.g. "Failed in
                # attempting to update the source: winget", which would otherwise
                # be parsed as a package row.
                if re.match(r"(failed|warning|error|unable|cannot|no packages)", line, re.IGNORECASE):
                    continue
                if line.startswith("Name") and "Version" in line:
                    # Record where each column starts so rows can be sliced by
                    # position; package names contain spaces, so splitting on
                    # whitespace would tear them apart.
                    bounds = []
                    for m in re.finditer(r"\S+", line):
                        bounds.append((m.start(), m.group()))
                    columns = {}
                    for idx, (start, title) in enumerate(bounds):
                        end = bounds[idx + 1][0] if idx + 1 < len(bounds) else None
                        columns[title.lower()] = (start, end)
                    header_cols = columns
                    continue
                parts = line.split()
                if len(parts) < 2 and not header_cols:
                    continue
                if header_cols:
                    row = {}
                    for title, (start, end) in header_cols.items():
                        value = line[start:end].strip() if end else line[start:].strip()
                        if value:
                            row[title] = value
                    if "name" not in row:
                        continue
                    if all(v.strip(" .").lower() in PackageManager._LIST_HEADERS for v in row.values()):
                        continue
                    pkg = {"name": row["name"], "version": row.get("version", "")}
                    if row.get("id"):
                        pkg["id"] = row["id"]
                    packages.append(pkg)
                    continue
                # Some managers (dotnet) use different header wording, so a row
                # made entirely of column titles is dropped here too.
                if all(p.strip(" .").lower() in PackageManager._LIST_HEADERS for p in parts):
                    continue
                pkg = {"name": parts[0], "version": parts[1] if len(parts) > 1 else ""}
                if len(parts) > 2:
                    pkg["id"] = parts[2]
                packages.append(pkg)
        return packages

    @staticmethod
    def update_all() -> Dict[str, List[Dict[str, Any]]]:
        results = {}
        for mgr in ("winget", "chocolatey", "scoop", "npm", "pip", "dotnet"):
            mgr_result = []
            code, stdout, stderr = PackageManager._run([mgr, "--version"])
            if code != 0:
                continue
            if mgr == "winget":
                rc, out, _ = PackageManager._run(
                    ["winget", "upgrade", "--all", "--accept-source-agreements",
                     "--accept-package-agreements", "--include-unknown"],
                    timeout=180,
                )
                mgr_result.append({
                    "success": rc == 0,
                    "manager": mgr,
                    "action": "update_all",
                    "stdout": out,
                    "error": None if rc == 0 else f"Exit code {rc}",
                })
            elif mgr == "chocolatey":
                rc, out, _ = PackageManager._run(["choco", "upgrade", "all", "-y"], timeout=180)
                mgr_result.append({
                    "success": rc == 0,
                    "manager": mgr,
                    "action": "update_all",
                    "stdout": out,
                })
            elif mgr == "scoop":
                rc, out, _ = PackageManager._run(["scoop", "update", "*"], timeout=180)
                mgr_result.append({
                    "success": rc == 0,
                    "manager": mgr,
                    "action": "update_all",
                    "stdout": out,
                })
            elif mgr == "npm":
                rc, out, _ = PackageManager._run(["npm", "update", "-g"], timeout=120)
                mgr_result.append({
                    "success": rc == 0,
                    "manager": mgr,
                    "action": "update_all",
                    "stdout": out,
                })
            elif mgr == "pip":
                rc, out, _ = PackageManager._run(
                    ["pip", "list", "--outdated", "--format=json"], timeout=30
                )
                if rc == 0 and out:
                    try:
                        outdated = json.loads(out)
                        for pkg in outdated:
                            pkg_name = pkg.get("name", "")
                            if pkg_name:
                                PackageManager._run(
                                    ["pip", "install", "--upgrade", pkg_name], timeout=60
                                )
                                mgr_result.append({
                                    "success": True,
                                    "manager": mgr,
                                    "action": "update",
                                    "package": pkg_name,
                                })
                    except json.JSONDecodeError:
                        pass
            elif mgr == "dotnet":
                rc, out, _ = PackageManager._run(
                    ["dotnet", "tool", "list", "-g", "--outdated"], timeout=30
                )
                if rc == 0 and out:
                    for line in out.split("\n"):
                        parts = line.strip().split()
                        if len(parts) >= 2 and parts[0] != "Package":
                            PackageManager._run(
                                ["dotnet", "tool", "update", "-g", parts[0]], timeout=60
                            )
                            mgr_result.append({
                                "success": True,
                                "manager": mgr,
                                "action": "update",
                                "package": parts[0],
                            })
            results[mgr] = mgr_result
        return results


class DevCacheCleaner(OptimizerBase):
    name = "Dev Cache Cleaner"
    description = "Clean npm, pip, docker, git, and IDE caches"
    category = OPTIMIZER_CATEGORY_SAFE
    benefit = "Frees disk space used by development tool caches"
    risks = "Will need to re-download packages"
    admin_required = False

    def run(self):
        deadline = time.time() + 60
        steps = [
            self._clean_npm, self._clean_pip, self._clean_docker,
            self._clean_git, self._clean_ide, self._clean_build,
            self._clean_rust, self._clean_dotnet, self._clean_go,
        ]
        for step in steps:
            if time.time() > deadline:
                self.add_result(False, "Dev cache cleanup timed out")
                break
            try:
                step(deadline)
            except Exception as e:
                self.add_result(False, f"{step.__name__} failed: {e}")
        return [r.to_dict() for r in self.results]

    def _walk_bounded(self, root_dir, deadline):
        try:
            for root, dirs, files in os.walk(root_dir):
                if time.time() > deadline:
                    break
                yield root, dirs, files
        except (PermissionError, OSError):
            pass

    def _run_cleanup(self, cmd: List[str], label: str, deadline: float, timeout: int = 30):
        if time.time() > deadline:
            return
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout)
            self.add_result(True, f"{label} cleaned")
        except FileNotFoundError:
            self.add_result(True, f"{label} not found, skipped")
        except subprocess.TimeoutExpired:
            self.add_result(False, f"{label} timed out")

    def _clean_npm(self, deadline):
        self._run_cleanup(["npm", "cache", "clean", "--force"], "npm cache", deadline)
        if time.time() > deadline:
            return
        home = os.path.expanduser("~")
        cleaned = 0
        for root, dirs, _ in self._walk_bounded(home, deadline):
            if "node_modules" in dirs:
                shutil.rmtree(os.path.join(root, "node_modules"), ignore_errors=True)
                cleaned += 1
            if cleaned >= 20 or time.time() > deadline:
                break
        if cleaned > 0:
            self.add_result(True, f"Removed {cleaned} node_modules folders")

    def _clean_pip(self, deadline):
        self._run_cleanup(["pip", "cache", "purge"], "pip cache", deadline)

    def _clean_docker(self, deadline):
        self._run_cleanup(["docker", "system", "prune", "-f"], "Docker", deadline, timeout=60)

    def _clean_git(self, deadline):
        try:
            home = os.path.expanduser("~")
            cleaned = 0
            for root, dirs, _ in self._walk_bounded(home, deadline):
                if ".git" in dirs:
                    subprocess.run(["git", "gc", "--auto", "--quiet"],
                                   cwd=root, capture_output=True, timeout=30)
                    cleaned += 1
                    dirs.remove(".git")
                if cleaned >= 30 or time.time() > deadline:
                    break
            self.add_result(True, f"Git garbage collected ({cleaned} repos)")
        except FileNotFoundError:
            self.add_result(True, "Git not found, skipped")

    def _clean_ide(self, deadline):
        home = os.path.expanduser("~")
        caches = []
        if CONFIG.os_type == "windows":
            caches = [
                os.path.join(home, "AppData", "Local", "JetBrains"),
                os.path.join(home, "AppData", "Local", "Microsoft", "VisualStudio"),
                os.path.join(home, "AppData", "Roaming", "Code", "Cache"),
                os.path.join(home, "AppData", "Roaming", "Code", "CachedData"),
                os.path.join(home, "AppData", "Roaming", "Code", "CachedExtensionVSIXs"),
                os.path.join(home, "AppData", "Local", "Temp", "JetBrains"),
            ]
        elif CONFIG.os_type == "macos":
            caches = [
                os.path.expanduser("~/Library/Caches/JetBrains"),
                os.path.expanduser("~/Library/Caches/com.microsoft.VSCode"),
                os.path.expanduser("~/Library/Caches/com.apple.Xcode"),
                os.path.expanduser("~/Library/Developer/Xcode/DerivedData"),
            ]
        elif CONFIG.os_type == "linux":
            caches = [
                os.path.join(home, ".cache", "JetBrains"),
                os.path.join(home, ".cache", "Code"),
                os.path.join(home, ".cache", "vim"),
                os.path.join(home, ".cache", "clangd"),
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
        self.add_result(True, f"IDE caches cleaned ({cleaned} dirs)")

    def _clean_build(self, deadline):
        home = os.path.expanduser("~")
        patterns = ["*.pyc", "*.pyo", "*.o", "*.obj", "*.class", "*.exe", "*.dll", "*.so", "*.dylib"]
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
                        break
        if cleaned > 0:
            self.add_result(True, f"Build artifacts cleaned ({cleaned} files)")

    def _clean_rust(self, deadline):
        self._run_cleanup(["cargo", "clean"], "Rust cargo", deadline)

    def _clean_dotnet(self, deadline):
        self._run_cleanup(["dotnet", "clean"], ".NET", deadline)

    def _clean_go(self, deadline):
        self._run_cleanup(["go", "clean", "-cache"], "Go cache", deadline)


class DevEnvironmentRepair:
    @staticmethod
    def _run(cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout, r.stderr
        except FileNotFoundError:
            return -1, "", f"{cmd[0]} not found"
        except subprocess.TimeoutExpired:
            return -2, "", "Timed out"
        except Exception as e:
            return -3, "", str(e)

    @staticmethod
    def fix_path_issues() -> Dict[str, Any]:
        issues = []
        fixed = 0
        path = os.environ.get("PATH", "")
        path_dirs = path.split(";") if CONFIG.os_type == "windows" else path.split(":")
        missing = []
        for d in path_dirs:
            d = d.strip()
            if d and not os.path.isdir(d):
                missing.append(d)
        if missing:
            issues.append(f"{len(missing)} non-existent directories in PATH")
        if CONFIG.os_type == "windows":
            common_tools = [
                r"C:\Windows\System32",
                r"C:\Windows",
                "%SystemRoot%\\System32\\Wbem",
                "%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\",
            ]
            for tool in common_tools:
                expanded = os.path.expandvars(tool)
                if expanded not in path_dirs and os.path.isdir(expanded):
                    pass
        return {
            "issues": issues,
            "path_count": len(path_dirs),
            "missing_dirs": missing[:10],
            "fixed": fixed,
            "healthy": len(issues) == 0,
        }

    @staticmethod
    def reset_npm_cache() -> Dict[str, Any]:
        code, stdout, stderr = DevEnvironmentRepair._run(["npm", "cache", "clean", "--force"])
        verify_code, verify_out, verify_err = "", "", ""
        if code == 0:
            verify_code, verify_out, verify_err = DevEnvironmentRepair._run(
                ["npm", "cache", "verify"]
            )
        return {
            "success": code == 0,
            "cache_cleaned": code == 0,
            "cache_verified": verify_code == 0,
            "stdout": stdout,
            "stderr": stderr,
            "verify_stdout": verify_out,
            "verify_stderr": verify_err,
            "error": stderr if code != 0 else (verify_err if verify_code != 0 else None),
        }

    @staticmethod
    def fix_pip_issues() -> Dict[str, Any]:
        actions = []
        code, out, err = DevEnvironmentRepair._run(
            ["python", "-m", "pip", "install", "--upgrade", "pip"]
        )
        pip_upgraded = code == 0
        actions.append("pip upgraded" if pip_upgraded else "pip upgrade failed")
        code2, out2, err2 = DevEnvironmentRepair._run(
            ["pip", "config", "set", "global.progress_bar", "off"]
        )
        actions.append("progress bar disabled" if code2 == 0 else "config unchanged")
        return {
            "success": pip_upgraded,
            "pip_upgraded": pip_upgraded,
            "pip_version": out.strip() if pip_upgraded else None,
            "actions": actions,
            "error": err if not pip_upgraded else None,
        }

    @staticmethod
    def regenerate_ssh_keys() -> Dict[str, Any]:
        ssh_dir = os.path.join(os.path.expanduser("~"), ".ssh")
        os.makedirs(ssh_dir, exist_ok=True)
        existing_keys = []
        for f in os.listdir(ssh_dir):
            if f in ("id_rsa", "id_ed25519", "id_ecdsa", "id_rsa.pub", "id_ed25519.pub", "id_ecdsa.pub"):
                existing_keys.append(f)
        generated = False
        key_path = None
        if not any(k.startswith("id_") and not k.endswith(".pub") for k in existing_keys):
            key_path = os.path.join(ssh_dir, "id_ed25519")
            code, out, err = DevEnvironmentRepair._run(
                ["ssh-keygen", "-t", "ed25519", "-f", key_path, "-N", "", "-q"],
                timeout=15,
            )
            if code == 0:
                generated = True
                existing_keys.append("id_ed25519")
                existing_keys.append("id_ed25519.pub")
            else:
                code2, out2, err2 = DevEnvironmentRepair._run(
                    ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f",
                     os.path.join(ssh_dir, "id_rsa"), "-N", "", "-q"],
                    timeout=15,
                )
                if code2 == 0:
                    generated = True
                    key_path = os.path.join(ssh_dir, "id_rsa")
                    existing_keys.append("id_rsa")
                    existing_keys.append("id_rsa.pub")
        return {
            "success": generated or len(existing_keys) > 0,
            "ssh_dir": ssh_dir,
            "existing_keys": existing_keys,
            "generated": generated,
            "key_path": key_path if generated else None,
            "healthy": bool(existing_keys),
        }

    @staticmethod
    def fix_git_config() -> Dict[str, Any]:
        issues = []
        fixed = []
        name = None
        email = None
        code, out, _ = DevEnvironmentRepair._run(["git", "config", "--global", "user.name"])
        if code == 0:
            name = out.strip()
        else:
            issues.append("git user.name not set")
            DevEnvironmentRepair._run(
                ["git", "config", "--global", "user.name", "Developer"]
            )
            fixed.append("Set user.name")
        code, out, _ = DevEnvironmentRepair._run(["git", "config", "--global", "user.email"])
        if code == 0:
            email = out.strip()
        else:
            issues.append("git user.email not set")
            DevEnvironmentRepair._run(
                ["git", "config", "--global", "user.email", "developer@example.com"]
            )
            fixed.append("Set user.email")
        crlf_code, _, _ = DevEnvironmentRepair._run(
            ["git", "config", "--global", "core.autocrlf"]
        )
        if crlf_code != 0:
            DevEnvironmentRepair._run(
                ["git", "config", "--global", "core.autocrlf", "true"]
            )
            fixed.append("Set core.autocrlf=true")
        for opt in ("pull.ff", "init.defaultBranch"):
            rc, _, _ = DevEnvironmentRepair._run(["git", "config", "--global", opt])
            if rc != 0:
                val = "only" if opt == "pull.ff" else "main"
                DevEnvironmentRepair._run(["git", "config", "--global", opt, val])
                fixed.append(f"Set {opt}={val}")
        return {
            "success": len(fixed) > 0 or len(issues) == 0,
            "issues": issues,
            "fixed": fixed,
            "user_name": name,
            "user_email": email,
            "healthy": len(issues) == 0,
        }
