import os
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..config import CONFIG
from ..logger import get_logger


logger = get_logger("reports")


_REPORT_DESCRIPTIONS = {
    "health": "System health assessment covering Windows, gaming, development, security, storage, and battery",
    "optimization": "Recent optimization history with before/after benchmark comparisons",
    "hardware": "Complete hardware inventory including CPU, GPU, RAM, storage, motherboard, and network",
    "driver": "Installed drivers with version dates and digital signature status",
    "battery": "Battery health metrics including capacity, cycle count, and estimated runtime",
    "network": "Network adapters, connection speeds, ping latency, and active connections",
}


class ReportGenerator:
    def __init__(self):
        self._reports_dir = os.path.join(CONFIG.base_dir, "data", "reports")
        self._index_path = os.path.join(self._reports_dir, "index.json")
        try:
            os.makedirs(self._reports_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create reports directory: {e}")

    def generate_report(self, report_type: str, format: str = "html") -> Dict:
        if report_type == "all":
            return self._generate_comprehensive_report(format)

        if report_type not in _REPORT_DESCRIPTIONS:
            return {"error": f"Unknown report type: {report_type}. Valid types: {', '.join(_REPORT_DESCRIPTIONS.keys())}, 'all'"}

        if format not in ("html", "json", "pdf"):
            return {"error": f"Unknown format: {format}. Valid formats: html, json, pdf"}

        try:
            collector = getattr(self, f"_collect_{report_type}_data", lambda: {})
            data = collector()
            data["report_type"] = report_type
            data["description"] = _REPORT_DESCRIPTIONS.get(report_type, "")
            data["generated_at"] = datetime.now().isoformat()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_id = f"{report_type}_{timestamp}"

            if format == "json":
                content = self.generate_json(data)
                ext = "json"
            elif format == "pdf":
                pdf_result = self.generate_pdf(report_type, data)
                if pdf_result:
                    return pdf_result
                content = self.generate_html(report_type, data)
                ext = "pdf.txt"
            else:
                content = self.generate_html(report_type, data)
                ext = "html"

            filename = f"{report_id}.{ext}"
            filepath = os.path.join(self._reports_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

            result = {
                "report_id": report_id,
                "type": report_type,
                "format": format,
                "path": filepath,
                "timestamp": data["generated_at"],
                "size": file_size,
            }

            if format == "json":
                result["content"] = data
            if format == "html":
                result["html"] = content

            self._update_index(result)
            logger.info(f"Generated {report_type} report: {report_id}.{ext}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate {report_type} report: {e}", exc_info=True)
            return {"error": str(e), "report_type": report_type, "format": format}

    def _generate_comprehensive_report(self, format: str) -> Dict:
        combined = {
            "report_type": "comprehensive",
            "description": "Complete system analysis covering all available metrics",
            "generated_at": datetime.now().isoformat(),
        }

        for rtype in _REPORT_DESCRIPTIONS:
            try:
                collector = getattr(self, f"_collect_{rtype}_data", lambda: {})
                combined[rtype] = collector()
            except Exception as e:
                logger.error(f"Failed to collect {rtype} data: {e}")
                combined[rtype] = {"error": str(e)}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_id = f"comprehensive_{timestamp}"

        if format == "json":
            content = self.generate_json(combined)
            ext = "json"
        elif format == "pdf":
            pdf_result = self.generate_pdf("comprehensive", combined)
            if pdf_result:
                return pdf_result
            content = self.generate_html("comprehensive", combined)
            ext = "pdf.txt"
        else:
            content = self.generate_html("comprehensive", combined)
            ext = "html"

        filepath = os.path.join(self._reports_dir, f"{report_id}.{ext}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

        result = {
            "report_id": report_id,
            "type": "comprehensive",
            "format": format,
            "path": filepath,
            "timestamp": combined["generated_at"],
            "size": file_size,
        }

        if format == "json":
            result["content"] = combined
        if format == "html":
            result["html"] = content

        self._update_index(result)
        return result

    def generate_html(self, report_type: str, data: Dict) -> str:
        report_title = report_type.replace("_", " ").title()
        timestamp = data.get("generated_at", datetime.now().isoformat())

        sections_html = self._build_sections(report_type, data)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Optinix - {report_title} Report</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #09090b; color: #e4e4e7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; line-height: 1.6; padding: 0; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 2rem; }}
  .header {{ background: linear-gradient(135deg, #18181b 0%, #27272a 100%); border-radius: 12px; padding: 2rem; margin-bottom: 2rem; border: 1px solid #27272a; }}
  .header h1 {{ font-size: 1.75rem; font-weight: 700; color: #fafafa; margin-bottom: 0.5rem; }}
  .header h1 span {{ color: #a78bfa; }}
  .header .meta {{ color: #a1a1aa; font-size: 0.875rem; display: flex; gap: 1.5rem; flex-wrap: wrap; }}
  .header .meta span {{ display: inline-flex; align-items: center; gap: 0.375rem; }}
  .section {{ background: #18181b; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.25rem; border: 1px solid #27272a; }}
  .section-title {{ font-size: 1.125rem; font-weight: 600; color: #fafafa; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #27272a; display: flex; align-items: center; gap: 0.5rem; }}
  .score-bar {{ height: 8px; background: #27272a; border-radius: 4px; overflow: hidden; margin: 0.5rem 0 0.25rem; }}
  .score-bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.6s ease; }}
  .score-excellent {{ background: linear-gradient(90deg, #22c55e, #16a34a); }}
  .score-good {{ background: linear-gradient(90deg, #22d3ee, #06b6d4); }}
  .score-fair {{ background: linear-gradient(90deg, #facc15, #eab308); }}
  .score-poor {{ background: linear-gradient(90deg, #fb923c, #f97316); }}
  .score-critical {{ background: linear-gradient(90deg, #f87171, #ef4444); }}
  .score-label {{ display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 0.125rem 0.5rem; border-radius: 4px; }}
  .badge {{ display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.75rem; font-weight: 500; padding: 0.125rem 0.5rem; border-radius: 9999px; }}
  .badge-good {{ background: rgba(34,197,94,0.15); color: #4ade80; }}
  .badge-warning {{ background: rgba(250,204,21,0.15); color: #facc15; }}
  .badge-critical {{ background: rgba(239,68,68,0.15); color: #f87171; }}
  .badge-info {{ background: rgba(59,130,246,0.15); color: #60a5fa; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
  th {{ text-align: left; padding: 0.625rem 0.75rem; color: #a1a1aa; font-weight: 500; border-bottom: 1px solid #27272a; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  td {{ padding: 0.625rem 0.75rem; border-bottom: 1px solid #1f1f23; color: #e4e4e7; }}
  tr:hover td {{ background: #1f1f23; }}
  .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }}
  .stat-card {{ background: #1f1f23; border-radius: 8px; padding: 1rem; border: 1px solid #27272a; }}
  .stat-card .label {{ font-size: 0.75rem; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat-card .value {{ font-size: 1.25rem; font-weight: 600; color: #fafafa; margin-top: 0.25rem; }}
  .stat-card .sub {{ font-size: 0.8125rem; color: #a1a1aa; margin-top: 0.125rem; }}
  .recommendation {{ background: #1f1f23; border-left: 3px solid #a78bfa; border-radius: 0 6px 6px 0; padding: 0.75rem 1rem; margin-bottom: 0.5rem; }}
  .recommendation p {{ color: #d4d4d8; font-size: 0.875rem; }}
  .timestamp {{ color: #71717a; font-size: 0.75rem; }}
  .divider {{ border: none; border-top: 1px solid #27272a; margin: 1.5rem 0; }}
  .status-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 0.375rem; }}
  .status-dot.active {{ background: #22c55e; }}
  .status-dot.inactive {{ background: #f87171; }}
  .status-dot.warning {{ background: #facc15; }}
  .footer {{ text-align: center; color: #52525b; font-size: 0.75rem; padding: 2rem 0 1rem; border-top: 1px solid #27272a; margin-top: 2rem; }}
  .footer a {{ color: #a78bfa; text-decoration: none; }}
  .error-box {{ background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 1rem; color: #f87171; }}
  @media (max-width: 640px) {{ .container {{ padding: 1rem; }} .header {{ padding: 1.25rem; }} .grid-2 {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1><span>Optinix</span> — {report_title} Report</h1>
    <div class="meta">
      <span>Generated: {timestamp}</span>
      <span>Report Type: {report_type}</span>
      {f'<span>Description: {data.get("description", "")}</span>' if data.get("description") else ''}
    </div>
  </div>
  {sections_html}
  <div class="footer">
    <p>Generated by Optinix Report Center &mdash; {timestamp}</p>
    <p><a href="#">Optinix PC Optimizer</a></p>
  </div>
</div>
</body>
</html>"""

    def _build_sections(self, report_type: str, data: Dict) -> str:
        if report_type == "comprehensive":
            html = ""
            for rtype in _REPORT_DESCRIPTIONS:
                section_data = data.get(rtype, {})
                if section_data:
                    html += self._build_sections(rtype, section_data)
            return html

        builder = getattr(self, f"_build_{report_type}_html", None)
        if builder:
            return builder(data)
        return "<div class='section'><p>No section data available.</p></div>"

    def _score_html(self, label: str, score: int, max_score: int = 100) -> str:
        pct = min(100, max(0, score / max_score * 100))
        if pct >= 85:
            cls = "score-excellent"
            badge = "badge-good"
            status = "Excellent"
        elif pct >= 65:
            cls = "score-good"
            badge = "badge-info"
            status = "Good"
        elif pct >= 45:
            cls = "score-fair"
            badge = "badge-warning"
            status = "Fair"
        elif pct >= 25:
            cls = "score-poor"
            badge = "badge-warning"
            status = "Poor"
        else:
            cls = "score-critical"
            badge = "badge-critical"
            status = "Critical"
        return f"""
    <div class="stat-card">
      <div class="label">{label}</div>
      <div class="value">{score}/100</div>
      <div class="score-bar"><div class="score-bar-fill {cls}" style="width:{pct}%"></div></div>
      <div class="sub"><span class="badge {badge}">{status}</span></div>
    </div>"""

    def _build_health_html(self, data: Dict) -> str:
        sections = ""
        scores_html = ""
        for key in ("windows_health", "gaming", "developer", "security", "storage", "battery", "pc_health"):
            entry = data.get(key)
            if isinstance(entry, dict) and "score" in entry:
                label = key.replace("_", " ").title()
                scores_html += self._score_html(label, entry["score"])
            elif isinstance(entry, (int, float)):
                scores_html += self._score_html(key.replace("_", " ").title(), entry)

        if scores_html:
            sections += f'<div class="section"><div class="section-title">Health Scores</div><div class="grid-2">{scores_html}</div></div>'

        details = {}
        for key in ("windows_health", "gaming", "developer", "security", "storage", "battery"):
            entry = data.get(key, {})
            if isinstance(entry, dict):
                d = entry.get("details", {})
                if isinstance(d, dict):
                    details[key] = d

        if details:
            rows = ""
            for category, dets in details.items():
                for k, v in dets.items():
                    v_str = str(v) if not isinstance(v, (list, dict)) else json.dumps(v)
                    rows += f"<tr><td>{category}</td><td>{k}</td><td>{v_str}</td></tr>"
            sections += f"""
    <div class="section">
      <div class="section-title">Detailed Metrics</div>
      <table><thead><tr><th>Category</th><th>Metric</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""

        if not sections:
            sections = "<div class='section'><p>No health data available.</p></div>"
        return sections

    def _build_optimization_html(self, data: Dict) -> str:
        sections = ""

        summary = data.get("summary", {})
        if summary:
            cards = f"""
    <div class="section">
      <div class="section-title">Optimization Summary</div>
      <div class="grid-2">
        <div class="stat-card"><div class="label">Total Optimizations</div><div class="value">{summary.get('total_optimizations', 0)}</div></div>
        <div class="stat-card"><div class="label">Total Successes</div><div class="value">{summary.get('total_success', 0)}</div></div>
        <div class="stat-card"><div class="label">Total Failures</div><div class="value" style="color:{'#f87171' if summary.get('total_failures', 0) > 0 else '#e4e4e7'}">{summary.get('total_failures', 0)}</div></div>
        <div class="stat-card"><div class="label">Avg Duration (ms)</div><div class="value">{round(summary.get('average_duration_ms', 0), 1)}</div></div>
      </div>
    </div>"""
            sections += cards

        entries = data.get("entries", data.get("recent_optimizations", []))
        if entries:
            rows = ""
            for e in entries[:20]:
                ts = e.get("timestamp", "")[:19] if e.get("timestamp") else ""
                rows += f"<tr><td>{ts}</td><td>{e.get('optimizer_name', '')}</td><td>{e.get('category', '')}</td><td><span class='badge {'badge-good' if e.get('error') is None else 'badge-critical'}'>{'Success' if e.get('error') is None else 'Failed'}</span></td></tr>"
            sections += f"""
    <div class="section">
      <div class="section-title">Recent Optimizations</div>
      <table><thead><tr><th>Timestamp</th><th>Optimizer</th><th>Category</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""

        if not sections:
            sections = "<div class='section'><p>No optimization data available.</p></div>"
        return sections

    def _build_hardware_html(self, data: Dict) -> str:
        sections = ""

        cpu = data.get("cpu", {})
        if cpu:
            sections += f"""
    <div class="section">
      <div class="section-title">CPU</div>
      <div class="grid-2">
        <div class="stat-card"><div class="label">Vendor</div><div class="value">{cpu.get('vendor', cpu.get('brand', 'N/A')).title()}</div></div>
        <div class="stat-card"><div class="label">Physical Cores</div><div class="value">{cpu.get('physical_cores', 'N/A')}</div></div>
        <div class="stat-card"><div class="label">Logical Cores</div><div class="value">{cpu.get('logical_cores', 'N/A')}</div></div>
        <div class="stat-card"><div class="label">Usage</div><div class="value">{cpu.get('percent', 'N/A')}%</div><div class="sub">Current utilization</div></div>
      </div>
    </div>"""

        gpu = data.get("gpu", {})
        if gpu:
            sections += f"""
    <div class="section">
      <div class="section-title">GPU</div>
      <div class="grid-2">
        <div class="stat-card"><div class="label">Name</div><div class="value" style="font-size:1rem">{gpu.get('name', 'N/A')}</div></div>
        <div class="stat-card"><div class="label">Usage</div><div class="value">{gpu.get('usage', 0)}%</div></div>
        <div class="stat-card"><div class="label">Memory</div><div class="value">{gpu.get('memory_used', 0)}/{gpu.get('memory_total', 0)} MB</div></div>
        <div class="stat-card"><div class="label">Driver</div><div class="value" style="font-size:0.875rem">{gpu.get('driver_version', gpu.get('driver', 'N/A'))}</div></div>
      </div>
    </div>"""

        ram = data.get("ram", {})
        if ram:
            sections += f"""
    <div class="section">
      <div class="section-title">Memory</div>
      <div class="grid-2">
        <div class="stat-card"><div class="label">Total</div><div class="value">{ram.get('total_gb', 0)} GB</div></div>
        <div class="stat-card"><div class="label">Used</div><div class="value">{ram.get('used_gb', 0)} GB</div></div>
        <div class="stat-card"><div class="label">Available</div><div class="value">{ram.get('available_gb', 0)} GB</div></div>
        <div class="stat-card"><div class="label">Usage</div><div class="value">{ram.get('percent', 0)}%</div></div>
      </div>
    </div>"""

        storage = data.get("storage", data.get("disk", []))
        if isinstance(storage, list) and storage:
            rows = ""
            for d in storage:
                if isinstance(d, dict):
                    rows += f"<tr><td>{d.get('device', d.get('mountpoint', 'N/A'))}</td><td>{d.get('total_gb', d.get('total', 0))} GB</td><td>{d.get('used_gb', d.get('used', 0))} GB</td><td>{d.get('free_gb', d.get('free', 0))} GB</td><td>{d.get('free_pct', d.get('percent', 0))}%</td></tr>"
            sections += f"""
    <div class="section">
      <div class="section-title">Storage</div>
      <table><thead><tr><th>Drive</th><th>Total</th><th>Used</th><th>Free</th><th>Usage</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""
        elif isinstance(storage, dict):
            drives = storage.get("drives", [])
            if drives:
                rows = ""
                for d in drives:
                    rows += f"<tr><td>{d.get('mount', d.get('device', 'N/A'))}</td><td>{d.get('total_gb', 0)} GB</td><td>{d.get('free_gb', 0)} GB</td><td>{d.get('free_pct', 0)}%</td><td>{'⚠️' if d.get('warning') else '✅'}</td></tr>"
                sections += f"""
    <div class="section">
      <div class="section-title">Storage</div>
      <table><thead><tr><th>Mount</th><th>Total</th><th>Free</th><th>Free %</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""

        system = data.get("system", {})
        if system:
            os_info = system.get("os", {})
            if isinstance(os_info, dict):
                os_str = f"{os_info.get('product', '')} (build {os_info.get('build', '')})"
            else:
                os_str = str(os_info)
            sections += f"""
    <div class="section">
      <div class="section-title">System</div>
      <div class="grid-2">
        <div class="stat-card"><div class="label">Operating System</div><div class="value" style="font-size:1rem">{os_str or 'N/A'}</div></div>
        <div class="stat-card"><div class="label">Laptop</div><div class="value">{'Yes' if system.get('is_laptop') else 'No'}</div></div>
        <div class="stat-card"><div class="label">Admin</div><div class="value">{'Yes' if system.get('is_admin') else 'No'}</div></div>
        <div class="stat-card"><div class="label">VM</div><div class="value">{'Yes' if system.get('is_vm') else 'No'}</div></div>
      </div>
    </div>"""

        motherboard = data.get("motherboard", data.get("baseboard", {}))
        if motherboard and isinstance(motherboard, dict):
            sections += f"""
    <div class="section">
      <div class="section-title">Motherboard</div>
      <div class="grid-2">
        <div class="stat-card"><div class="label">Manufacturer</div><div class="value" style="font-size:0.875rem">{motherboard.get('manufacturer', 'N/A')}</div></div>
        <div class="stat-card"><div class="label">Product</div><div class="value" style="font-size:0.875rem">{motherboard.get('product', 'N/A')}</div></div>
        <div class="stat-card"><div class="label">Version</div><div class="value" style="font-size:0.875rem">{motherboard.get('version', 'N/A')}</div></div>
        <div class="stat-card"><div class="label">Serial</div><div class="value" style="font-size:0.75rem">{motherboard.get('serial', 'N/A')}</div></div>
      </div>
    </div>"""

        if not sections:
            sections = "<div class='section'><p>No hardware data available.</p></div>"
        return sections

    def _build_driver_html(self, data: Dict) -> str:
        sections = ""

        drivers = data.get("drivers", [])
        if drivers:
            rows = ""
            for d in drivers[:50]:
                name = d.get("name", d.get("DeviceName", "N/A"))
                version = d.get("version", d.get("DriverVersion", "N/A"))
                date = d.get("date", d.get("DriverDate", ""))
                mfr = d.get("manufacturer", d.get("Manufacturer", ""))
                cls = d.get("class", d.get("DeviceClass", ""))
                rows += f"<tr><td>{name}</td><td>{version}</td><td>{date}</td><td>{mfr}</td><td>{cls}</td></tr>"
            sections += f"""
    <div class="section">
      <div class="section-title">Installed Drivers <span class="timestamp">({len(drivers)} total)</span></div>
      <table><thead><tr><th>Driver</th><th>Version</th><th>Date</th><th>Manufacturer</th><th>Class</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""

        missing = data.get("missing", [])
        if missing:
            rows = ""
            for d in missing:
                rows += f"<tr><td>{d.get('name', d.get('FriendlyName', 'Unknown'))}</td><td>{d.get('class', d.get('Class', ''))}</td><td><span class='badge badge-critical'>Missing</span></td></tr>"
            sections += f"""
    <div class="section">
      <div class="section-title">Missing / Problem Drivers <span class="timestamp">({len(missing)} issues)</span></div>
      <table><thead><tr><th>Device</th><th>Class</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""

        if not sections:
            sections = "<div class='section'><p>No driver data available.</p></div>"
        return sections

    def _build_battery_html(self, data: Dict) -> str:
        sections = ""

        is_laptop = data.get("is_laptop", data.get("details", {}).get("is_laptop", False))
        if not is_laptop:
            sections += """
    <div class="section">
      <div class="section-title">Battery Status</div>
      <div class="stat-card"><div class="value">Desktop System</div><div class="sub">No battery detected. This system is not a laptop.</div></div>
    </div>"""
            return sections

        health = data.get("health_pct", data.get("details", {}).get("health_pct"))
        cycles = data.get("cycle_count", data.get("details", {}).get("cycle_count"))
        runtime = data.get("est_runtime_min", data.get("details", {}).get("est_runtime_min"))

        score = data.get("score")
        cards = ""
        if health is not None:
            cards += f'<div class="stat-card"><div class="label">Battery Health</div><div class="value">{health}%</div></div>'
        if cycles is not None:
            cards += f'<div class="stat-card"><div class="label">Cycle Count</div><div class="value">{cycles}</div></div>'
        if runtime is not None:
            cards += f'<div class="stat-card"><div class="label">Est. Runtime</div><div class="value">{runtime} min</div></div>'
        if score is not None:
            pct = min(100, max(0, score))
            cards += self._score_html("Battery Score", score)

        if cards:
            sections += f'<div class="section"><div class="section-title">Battery Metrics</div><div class="grid-2">{cards}</div></div>'

        if not sections:
            sections = "<div class='section'><p>No battery data available.</p></div>"
        return sections

    def _build_network_html(self, data: Dict) -> str:
        sections = ""

        adapters = data.get("adapters", [])
        if adapters:
            rows = ""
            for a in adapters:
                name = a.get("name", a.get("Name", "N/A"))
                desc = a.get("description", a.get("InterfaceDescription", ""))
                speed = a.get("speed", a.get("LinkSpeed", "N/A"))
                status_dot = "active" if a.get("status", a.get("Status", "")) == "Up" else "inactive"
                rows += f"<tr><td>{name}</td><td style='font-size:0.8125rem'>{desc}</td><td>{speed}</td><td><span class='status-dot {status_dot}'></span>{a.get('status', a.get('Status', 'Unknown'))}</td></tr>"
            sections += f"""
    <div class="section">
      <div class="section-title">Network Adapters</div>
      <table><thead><tr><th>Name</th><th>Description</th><th>Speed</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""

        ping = data.get("ping", {})
        if ping:
            sections += f"""
    <div class="section">
      <div class="section-title">Ping Latency</div>
      <div class="grid-2">
        <div class="stat-card"><div class="label">Host</div><div class="value" style="font-size:0.875rem">{ping.get('host', 'N/A')}</div></div>
        <div class="stat-card"><div class="label">Avg Latency</div><div class="value">{ping.get('avg', 0)} ms</div></div>
        <div class="stat-card"><div class="label">Min</div><div class="value">{ping.get('min', 0)} ms</div></div>
        <div class="stat-card"><div class="label">Max</div><div class="value">{ping.get('max', 0)} ms</div></div>
        <div class="stat-card"><div class="label">Packet Loss</div><div class="value" style="color:{'#f87171' if ping.get('packet_loss', 0) > 0 else '#4ade80'}">{ping.get('packet_loss', 0)}%</div></div>
      </div>
    </div>"""

        connections = data.get("connections", [])
        if connections:
            rows = ""
            for c in connections[:30]:
                rows += f"<tr><td>{c.get('protocol', 'N/A')}</td><td>{c.get('local_addr', '')}:{c.get('local_port', '')}</td><td>{c.get('remote_addr', '')}:{c.get('remote_port', '')}</td><td>{c.get('status', '')}</td></tr>"
            sections += f"""
    <div class="section">
      <div class="section-title">Active Connections <span class="timestamp">({len(connections)} total)</span></div>
      <table><thead><tr><th>Protocol</th><th>Local</th><th>Remote</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
    </div>"""

        if not sections:
            sections = "<div class='section'><p>No network data available.</p></div>"
        return sections

    def generate_json(self, data: Dict) -> str:
        return json.dumps(data, indent=2, default=str)

    def generate_pdf(self, report_type: str, data: Dict) -> Optional[Dict]:
        try:
            import weasyprint
            html = self.generate_html(report_type, data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_id = f"{report_type}_{timestamp}"
            filepath = os.path.join(self._reports_dir, f"{report_id}.pdf")
            weasyprint.HTML(string=html).write_pdf(filepath)
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            result = {
                "report_id": report_id,
                "type": report_type,
                "format": "pdf",
                "path": filepath,
                "timestamp": data.get("generated_at", datetime.now().isoformat()),
                "size": file_size,
            }
            self._update_index(result)
            logger.info(f"Generated PDF report: {report_id}.pdf")
            return result
        except ImportError:
            logger.info("weasyprint not available, trying pdfkit...")
        except Exception as e:
            logger.warning(f"weasyprint failed: {e}")

        try:
            import pdfkit
            html = self.generate_html(report_type, data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_id = f"{report_type}_{timestamp}"
            filepath = os.path.join(self._reports_dir, f"{report_id}.pdf")
            pdfkit.from_string(html, filepath)
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            result = {
                "report_id": report_id,
                "type": report_type,
                "format": "pdf",
                "path": filepath,
                "timestamp": data.get("generated_at", datetime.now().isoformat()),
                "size": file_size,
            }
            self._update_index(result)
            logger.info(f"Generated PDF report: {report_id}.pdf")
            return result
        except ImportError:
            logger.warning("pdfkit also not available. Falling back to HTML with .pdf.txt extension.")
        except Exception as e:
            logger.warning(f"pdfkit failed: {e}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_id = f"{report_type}_{timestamp}"
        html = self.generate_html(report_type, data)
        filepath = os.path.join(self._reports_dir, f"{report_id}.pdf.txt")
        note = (
            "\n\n<!-- PDF generation requires weasyprint or pdfkit.\n"
            "Install with: pip install weasyprint\n"
            "Or: pip install pdfkit\n"
            "This file contains the HTML that would be converted to PDF. -->\n"
        )
        html = html.replace("</html>", f"{note}</html>")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        result = {
            "report_id": report_id,
            "type": report_type,
            "format": "pdf",
            "path": filepath,
            "timestamp": data.get("generated_at", datetime.now().isoformat()),
            "size": file_size,
            "note": "PDF library not available. Saved as HTML with .pdf.txt extension.",
        }
        self._update_index(result)
        logger.info(f"Saved PDF fallback: {report_id}.pdf.txt")
        return result

    def _collect_health_data(self) -> Dict:
        try:
            from ..intelligence.health_scorer import HealthScorer
            scorer = HealthScorer()
            return scorer.score_all()
        except Exception as e:
            logger.error(f"Failed to collect health data: {e}")
            return {"error": str(e), "scores": {}}

    def _collect_optimization_data(self) -> Dict:
        try:
            from ..optimization_history import OptimizationHistory
            history = OptimizationHistory()
            data = {}
            data["summary"] = history.get_summary()
            data["entries"] = history.get_all(limit=50).get("entries", [])
            return data
        except Exception as e:
            logger.error(f"Failed to collect optimization data: {e}")
            return {"error": str(e)}

    def _collect_hardware_data(self) -> Dict:
        try:
            from ..hardware_detection import HardwareDetector
            detector = HardwareDetector()
            data = detector.detect_all()

            try:
                from ..scanner import SystemScanner
                scanner = SystemScanner(CONFIG.os_type)
                scan = scanner.full_scan()
                if "cpu" in scan and scan["cpu"]:
                    data["cpu"]["percent"] = scan["cpu"].get("percent", 0)
                    data["cpu"]["freq"] = scan["cpu"].get("freq")
                    data["cpu"]["temperature"] = scan["cpu"].get("temperature")
                if "gpu" in scan and scan["gpu"]:
                    data["gpu"]["usage"] = scan["gpu"].get("usage", 0)
                    data["gpu"]["memory_used"] = scan["gpu"].get("memory_used", 0)
                    data["gpu"]["memory_total"] = scan["gpu"].get("memory_total", 0)
                    data["gpu"]["temperature"] = scan["gpu"].get("temperature", 0)
                    if scan["gpu"].get("driver"):
                        data["gpu"]["driver_version"] = scan["gpu"]["driver"]
                if "memory" in scan and scan["memory"]:
                    data["ram"] = scan["memory"]
                if "disk" in scan:
                    data["storage"] = scan["disk"]
                if "system" in scan:
                    data["system"]["uptime"] = scan["system"].get("uptime", "N/A")
                    data["system"]["platform"] = scan["system"].get("platform", "")
            except Exception as e:
                logger.warning(f"Scanner data merge failed: {e}")

            if "storage" not in data:
                try:
                    data["storage"] = detector.detect_disk_type()
                except Exception:
                    pass

            try:
                r = self._ps(
                    "Get-CimInstance Win32_BaseBoard -EA SilentlyContinue | Select-Object Manufacturer,Product,Version,SerialNumber | ConvertTo-Json -Compress"
                )
                if r.stdout.strip():
                    import json
                    mb = json.loads(r.stdout.strip())
                    if isinstance(mb, list):
                        mb = mb[0] if mb else {}
                    if isinstance(mb, dict):
                        data["motherboard"] = {
                            "manufacturer": mb.get("Manufacturer", "N/A"),
                            "product": mb.get("Product", "N/A"),
                            "version": mb.get("Version", "N/A"),
                            "serial": mb.get("SerialNumber", "N/A"),
                        }
            except Exception as e:
                logger.debug(f"Motherboard detection failed: {e}")

            return data
        except Exception as e:
            logger.error(f"Failed to collect hardware data: {e}")
            return {"error": str(e)}

    def _collect_driver_data(self) -> Dict:
        try:
            from ..drivers import DriverManager
            mgr = DriverManager(CONFIG.os_type)
            data = {
                "drivers": mgr.scan_drivers(),
                "missing": mgr.get_missing_drivers(),
            }
            return data
        except Exception as e:
            logger.error(f"Failed to collect driver data: {e}")
            return {"error": str(e), "drivers": [], "missing": []}

    def _collect_battery_data(self) -> Dict:
        try:
            from ..intelligence.health_scorer import HealthScorer
            scorer = HealthScorer()
            battery = scorer.get_score("battery")
            return battery
        except Exception as e:
            logger.error(f"Failed to collect battery data: {e}")
            return {"error": str(e)}

    def _collect_network_data(self) -> Dict:
        data = {}
        try:
            adapters = []
            try:
                r = self._ps(
                    "Get-NetAdapter -EA SilentlyContinue | Select-Object Name,InterfaceDescription,MacAddress,LinkSpeed,Status | ConvertTo-Json -Compress"
                )
                if r.stdout.strip():
                    import json
                    parsed = json.loads(r.stdout.strip())
                    if isinstance(parsed, dict):
                        parsed = [parsed]
                    adapters = [
                        {
                            "name": a.get("Name", ""),
                            "description": a.get("InterfaceDescription", ""),
                            "mac": a.get("MacAddress", ""),
                            "speed": a.get("LinkSpeed", ""),
                            "status": a.get("Status", ""),
                        }
                        for a in (parsed if isinstance(parsed, list) else [])
                    ]
            except Exception as e:
                logger.debug(f"Adapter query failed: {e}")

            if not adapters:
                try:
                    import psutil
                    for name, stats in psutil.net_if_stats().items():
                        if stats.isup:
                            adapters.append({
                                "name": name,
                                "description": name,
                                "mac": "",
                                "speed": f"{stats.speed} Mbps" if stats.speed > 0 else "N/A",
                                "status": "Up",
                            })
                except Exception:
                    pass

            data["adapters"] = adapters
        except Exception as e:
            logger.error(f"Failed to collect adapter data: {e}")
            data["adapters"] = []

        try:
            from ..speed_test import SpeedTest
            tester = SpeedTest()
            ping = tester.test_ping()
            data["ping"] = ping
        except Exception as e:
            logger.debug(f"Ping test failed: {e}")
            try:
                r = self._run(["ping", "-n", "4", "8.8.8.8"], timeout=15)
                lines = r.stdout.splitlines()
                data["ping"] = {"host": "8.8.8.8", "raw": r.stdout}
            except Exception:
                data["ping"] = {"host": "8.8.8.8", "error": "Ping failed"}

        try:
            import psutil
            connections = []
            for c in psutil.net_connections():
                try:
                    laddr = f"{c.laddr.ip}" if c.laddr else ""
                    lport = c.laddr.port if c.laddr else ""
                    raddr = f"{c.raddr.ip}" if c.raddr else ""
                    rport = c.raddr.port if c.raddr else ""
                    connections.append({
                        "protocol": "TCP" if c.type == 1 else "UDP" if c.type == 2 else str(c.type),
                        "local_addr": laddr,
                        "local_port": lport,
                        "remote_addr": raddr,
                        "remote_port": rport,
                        "status": c.status,
                    })
                except Exception:
                    continue
            data["connections"] = connections
        except Exception as e:
            logger.debug(f"Connection scan failed: {e}")
            data["connections"] = []

        data["generated_at"] = datetime.now().isoformat()
        return data

    def _run(self, cmd, timeout=10):
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out: {' '.join(cmd)}")
            return type("", (), {"returncode": -1, "stdout": "", "stderr": ""})()
        except Exception as e:
            logger.debug(f"Command failed: {e}")
            return type("", (), {"returncode": -1, "stdout": "", "stderr": ""})()

    def _ps(self, cmd, timeout=10):
        return self._run(
            ["powershell", "-NoProfile", "-Command", cmd], timeout=timeout
        )

    def _update_index(self, entry: Dict):
        index = self._load_index()
        index[entry["report_id"]] = {
            "report_id": entry["report_id"],
            "type": entry["type"],
            "format": entry["format"],
            "path": entry["path"],
            "timestamp": entry["timestamp"],
            "size": entry["size"],
        }
        try:
            with open(self._index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to update report index: {e}")

    def _load_index(self) -> Dict:
        if not os.path.isfile(self._index_path):
            return {}
        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load report index: {e}")
            return {}

    def list_reports(self, report_type: str = None, limit: int = 20) -> List[Dict]:
        index = self._load_index()
        reports = list(index.values())
        if report_type:
            reports = [r for r in reports if r["type"] == report_type]
        reports.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return reports[:limit]

    def get_report(self, report_id: str) -> Optional[Dict]:
        index = self._load_index()
        entry = index.get(report_id)
        if not entry:
            return None
        path = entry.get("path")
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    entry["content"] = f.read()
            except OSError as e:
                logger.error(f"Failed to read report file: {e}")
                entry["content"] = None
        return entry

    def delete_report(self, report_id: str) -> bool:
        index = self._load_index()
        entry = index.pop(report_id, None)
        if not entry:
            return False
        path = entry.get("path")
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError as e:
                logger.error(f"Failed to delete report file: {e}")
        try:
            with open(self._index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to update index after delete: {e}")
            return False
        logger.info(f"Deleted report: {report_id}")
        return True


report_generator = ReportGenerator()
