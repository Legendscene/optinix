/**
 * Information architecture for Optinix.
 *
 * 12 destinations group 53 tools. The sidebar shows the 12 destinations plus
 * whatever the user pins. Every tool stays reachable through its destination
 * hub, the command palette, or a direct route - nothing is removed, it is
 * just no longer a wall.
 *
 * Route ids: destinations and tools share one namespace, so no tool id may
 * equal a destination id (the old shell had four such collisions and the
 * tools behind them were unreachable). Renamed: gaming -> game-tweaks,
 * network -> network-tuning, diagnostics -> troubleshooter, settings ->
 * general. The tool `home` was folded into the `home` destination.
 */
import type { ComponentType } from 'react'
import {
  Home, Gauge, Gamepad2, Library, Network, Zap, Activity, Stethoscope,
  FileText, History, Palette, Settings2,
  LayoutDashboard, Cpu, MemoryStick, HardDrive, HeartPulse, LineChart,
  Rocket, Mouse, CircuitBoard, BatteryCharging, Battery, Crosshair,
  Eraser, FolderTree, Files, Undo2, Bell, Trash2, Sparkles, Power,
  SlidersHorizontal, Calendar, Layers, Sliders, FileCode, Shield, Users,
  Info, ScanLine, Download, Package, Wrench, RadioTower, Briefcase,
  Terminal, Boxes, Puzzle, Store, Wand, BrainCircuit, Monitor, Globe,
} from 'lucide-react'

/** Lucide components all share this shape; avoids depending on the LucideIcon export. */
export type IconComponent = ComponentType<{
  size?: number | string
  className?: string
  strokeWidth?: number
}>

export type ZoneId =
  | 'home' | 'performance' | 'gaming' | 'games' | 'network' | 'optimizer'
  | 'monitor' | 'diagnostics' | 'reports' | 'history' | 'personalization'
  | 'settings'

export interface Zone {
  id: ZoneId
  label: string
  tagline: string
  icon: IconComponent
  /** Shown on the destination hub so the user knows what the area is for. */
  purpose: string
}

export interface Tool {
  /** Route id, matches the page registry in App.tsx. */
  id: string
  label: string
  zone: ZoneId
  icon: IconComponent
  /** One line, plain language, no marketing tone. */
  description: string
  /** Sub-heading inside a destination hub. */
  group: string
  /** Extra search terms so "ram", "dns", "junk" all land somewhere sensible. */
  keywords: string[]
  badge?: 'danger' | 'admin' | 'beta'
  /** Pinned to the top of the destination hub. */
  primary?: boolean
}

/**
 * Route ids older builds may still have stored (localStorage / hashes) or
 * that the backend emits. Mapped to their successor destination. Only
 * applied when the id is otherwise invalid, so a tool id that happens to
 * match an old zone id (e.g. `cleanup`) still opens the tool page.
 */
export const LEGACY_ROUTES: Record<string, string> = {
  overview: 'home',
  optimize: 'optimizer',
  system: 'optimizer',
}

export const ZONES: Zone[] = [
  {
    id: 'home',
    label: 'Home',
    tagline: 'Health, live metrics and what needs attention',
    icon: Home,
    purpose: 'Answer whether the machine is healthy right now, and what Optinix has done to it.',
  },
  {
    id: 'performance',
    label: 'Performance',
    tagline: 'CPU, GPU, memory, storage and tuning',
    icon: Gauge,
    purpose: 'Inspect and tune the hardware that decides how fast everything runs.',
  },
  {
    id: 'gaming',
    label: 'Gaming',
    tagline: 'Frame rate, input latency and power',
    icon: Gamepad2,
    purpose: 'Tune the parts of the system that decide frame time and input lag.',
  },
  {
    id: 'games',
    label: 'Games',
    tagline: 'Library, profiles and quick launch',
    icon: Library,
    purpose: 'Every game Optinix knows about, with the profile that will be applied to it.',
  },
  {
    id: 'network',
    label: 'Network',
    tagline: 'Latency, DNS and connection quality',
    icon: Network,
    purpose: 'Reduce ping, stabilise the connection and find where the problem actually is.',
  },
  {
    id: 'optimizer',
    label: 'Optimizer',
    tagline: 'One-click pass, cleanup, startup and tweaks',
    icon: Zap,
    purpose: 'Change how the machine behaves. These tools apply real system changes and can be rolled back.',
  },
  {
    id: 'monitor',
    label: 'Monitor',
    tagline: 'Second-by-second live metrics',
    icon: Activity,
    purpose: 'Watch CPU, GPU, RAM, disk, network and temperatures as they move.',
  },
  {
    id: 'diagnostics',
    label: 'Diagnostics',
    tagline: 'Health scores, drivers and troubleshooting',
    icon: Stethoscope,
    purpose: 'Find what is wrong - hardware, drivers, security - before it becomes a problem.',
  },
  {
    id: 'reports',
    label: 'Reports',
    tagline: 'Generated system reports',
    icon: FileText,
    purpose: 'Produce and read system reports you can keep or share.',
  },
  {
    id: 'history',
    label: 'History',
    tagline: 'Timeline, notifications and rollback',
    icon: History,
    purpose: 'Every change Optinix has made, when it happened, and how to undo it.',
  },
  {
    id: 'personalization',
    label: 'Personalization',
    tagline: 'Theme, accent and density',
    icon: Palette,
    purpose: 'How Optinix looks. No system changes here.',
  },
  {
    id: 'settings',
    label: 'Settings',
    tagline: 'Preferences, tools and AI',
    icon: Settings2,
    purpose: 'How Optinix behaves: startup, integrations and optional tooling.',
  },
]

export const ZONE_MAP: Record<ZoneId, Zone> = Object.fromEntries(
  ZONES.map((z) => [z.id, z]),
) as Record<ZoneId, Zone>

export const TOOLS: Tool[] = [
  // ------------------------------------------------------------------ home
  {
    id: 'dashboard', label: 'Dashboard', zone: 'home', group: 'Start here',
    icon: LayoutDashboard,
    description: 'Detailed dashboard with every module tile and per-module actions.',
    keywords: ['dashboard', 'tiles', 'modules', 'classic', 'detailed', 'all modules'],
  },

  // ----------------------------------------------------------- performance
  {
    id: 'cpu', label: 'CPU', zone: 'performance', group: 'Hardware',
    icon: Cpu, primary: true,
    description: 'Core topology, affinity, scheduling priority and per-core load.',
    keywords: ['cpu', 'processor', 'cores', 'threads', 'affinity', 'priority', 'scaling'],
  },
  {
    id: 'gpu', label: 'GPU', zone: 'performance', group: 'Hardware',
    icon: Monitor, primary: true,
    description: 'Adapter details, VRAM, hardware-accelerated scheduling and driver tuning.',
    keywords: ['gpu', 'graphics', 'video', 'vram', 'nvidia', 'amd', 'radeon', 'geforce', 'nvidia-smi'],
  },
  {
    id: 'memory', label: 'Memory', zone: 'performance', group: 'Hardware',
    icon: MemoryStick, primary: true,
    description: 'Per-process RAM usage, working-set trimming and page file review.',
    keywords: ['ram', 'memory', 'oom', 'leak', 'working set', 'cache', 'pagefile', 'virtual'],
  },
  {
    id: 'storage', label: 'Storage', zone: 'performance', group: 'Storage',
    icon: HardDrive, primary: true,
    description: 'Per-drive usage, TRIM for SSDs, defrag for HDDs and SMART health.',
    keywords: ['storage', 'disk', 'drive', 'trim', 'defrag', 'smart', 'free space', 'used space', 'ssd', 'hdd'],
  },
  {
    id: 'storage-map', label: 'Storage Map', zone: 'performance', group: 'Storage',
    icon: FolderTree, primary: true,
    description: 'Visual treemap of what is actually eating the drive, by folder and type.',
    keywords: ['storage map', 'treemap', 'folder size', 'what is using space', 'visual', 'largest folder', 'breakdown'],
  },
  {
    id: 'overclock', label: 'Overclock', zone: 'performance', group: 'Tuning',
    icon: Gauge, badge: 'admin',
    description: 'CPU timing, power limits, timer resolution and core parking.',
    keywords: ['overclock', 'turbo', 'timing', 'power limit', 'undervolt', 'latency', 'timer'],
  },
  {
    id: 'extreme', label: 'Extreme Mode', zone: 'performance', group: 'Tuning',
    icon: Rocket, badge: 'danger',
    description: 'Aggressive tuning for maximum frame rate. Every step is snapshotted first.',
    keywords: ['extreme', 'overdrive', 'max', 'turbo', 'aggressive', 'hardcore', 'unsafe'],
  },

  // ---------------------------------------------------------------- gaming
  {
    id: 'game-tweaks', label: 'Game Tweaks', zone: 'gaming', group: 'Performance',
    icon: Gamepad2, primary: true,
    description: 'Game Mode, Game DVR, fullscreen optimisation, mouse acceleration and shader cache.',
    keywords: ['game', 'gaming', 'fps', 'dvr', 'game mode', 'fullscreen', 'mouse acceleration', 'shader'],
  },
  {
    id: 'game-mode', label: 'Game Mode', zone: 'gaming', group: 'Performance',
    icon: Crosshair, primary: true,
    description: 'Detect running games, apply per-game profiles and set timer resolution.',
    keywords: ['game mode', 'profile', 'per game', 'timer resolution', 'detect game', 'boost game'],
  },
  {
    id: 'peripheral', label: 'Peripherals', zone: 'gaming', group: 'Input',
    icon: Mouse, primary: true,
    description: 'Mouse polling rate, keyboard rollover, USB and NVMe controller tuning.',
    keywords: ['mouse', 'keyboard', 'polling', 'usb', 'rollover', 'nvme', 'controller', 'dpi', 'hid'],
  },
  {
    id: 'power', label: 'Power Plans', zone: 'gaming', group: 'Power',
    icon: Battery, primary: true,
    description: 'List and switch between Balanced, High performance and Ultimate performance.',
    keywords: ['power', 'plan', 'balanced', 'high performance', 'ultimate', 'energy', 'throttle'],
  },
  {
    id: 'power-center', label: 'Power Center', zone: 'gaming', group: 'Power',
    icon: BatteryCharging,
    description: 'Sleep, hibernate, USB suspend, PCIe link state and processor scaling.',
    keywords: ['power', 'sleep', 'hibernate', 'suspend', 'pcie', 'aspm', 'battery', 'charger', 'scaling'],
  },
  {
    id: 'bios', label: 'BIOS', zone: 'gaming', group: 'Firmware',
    icon: CircuitBoard, badge: 'admin',
    description: 'Motherboard and firmware details with the settings worth changing.',
    keywords: ['bios', 'uefi', 'firmware', 'motherboard', 'mainboard', 'xmp', 'expo', 'boot order'],
  },

  // --------------------------------------------------------------- network
  {
    id: 'network-tuning', label: 'Network Optimizer', zone: 'network', group: 'Tuning',
    icon: Network, primary: true,
    description: 'TCP stack tuning, adapter presets, MTU, port range and bufferbloat control.',
    keywords: ['network', 'tcp', 'mtu', 'adapter', 'bufferbloat', 'latency', 'jitter', 'tuning', 'winsock'],
  },
  {
    id: 'internet', label: 'Internet Booster', zone: 'network', group: 'Tuning',
    icon: RadioTower, primary: true,
    description: 'One-tap DNS, Nagle, autotuning and congestion control changes.',
    keywords: ['internet', 'booster', 'dns', 'nagle', 'speed', 'faster', 'ping', 'google', 'cloudflare'],
  },
  {
    id: 'speed-test', label: 'Speed Test', zone: 'network', group: 'Measure',
    icon: Activity, primary: true,
    description: 'Measure ping, download and upload before and after tuning.',
    keywords: ['speed test', 'bandwidth', 'download', 'upload', 'throughput', 'latency', 'ping', 'measure'],
  },
  {
    id: 'network-intelligence', label: 'Network Intelligence', zone: 'network', group: 'Measure',
    icon: Globe, primary: true,
    description: 'Latency, jitter and packet-loss probes to any host, with route trace and DNS details.',
    keywords: ['network intelligence', 'latency', 'jitter', 'packet loss', 'route', 'traceroute', 'trace', 'dns', 'icmp', 'ping', 'hop', 'diagnostics', 'connection quality'],
  },

  // -------------------------------------------------------------- optimizer
  {
    id: 'oneclick', label: 'One Click Optimize', zone: 'optimizer', group: 'Quick actions',
    icon: Zap, primary: true,
    description: 'Runs the full safe optimisation pass across every module.',
    keywords: ['one click', 'optimize', 'boost', 'auto', 'quick', 'fix', 'speed up', 'tune'],
  },
  {
    id: 'ai-optimizer', label: 'AI Optimizer', zone: 'optimizer', group: 'Quick actions',
    icon: Sparkles, primary: true,
    description: 'Finds bottlenecks and proposes fixes. Works fully offline with heuristics.',
    keywords: ['ai', 'smart', 'recommend', 'suggest', 'automatic', 'bottleneck', 'advice'],
  },
  {
    id: 'cleanup', label: 'Cleanup', zone: 'optimizer', group: 'Junk',
    icon: Eraser, primary: true,
    description: 'Temp files, caches, crash dumps, logs, thumbnails and Recycle Bin.',
    keywords: ['cleanup', 'clean', 'junk', 'temp', 'cache', 'recycle bin', 'dumps', 'thumbnails', 'free space'],
  },
  {
    id: 'file-tools', label: 'File Tools', zone: 'optimizer', group: 'Junk',
    icon: Files, primary: true,
    description: 'Find duplicates by hash, list large files and securely shred data.',
    keywords: ['duplicate', 'large file', 'shred', 'wipe', 'secure delete', 'find files', 'dedupe', 'bloat'],
  },
  {
    id: 'startup', label: 'Startup Manager', zone: 'optimizer', group: 'Startup and background',
    icon: Power, primary: true,
    description: 'Enable or disable programs that run at boot, from Task Manager and Run keys.',
    keywords: ['startup', 'boot', 'autostart', 'run key', 'task manager', 'slow boot', 'login'],
  },
  {
    id: 'services', label: 'Services', zone: 'optimizer', group: 'Startup and background',
    icon: SlidersHorizontal, primary: true,
    description: 'Stop and disable Windows services. Flags anything unsafe to touch.',
    keywords: ['service', 'daemon', 'svchost', 'background', 'telemetry', 'disable', 'windows update'],
  },
  {
    id: 'windows', label: 'Windows Tweaks', zone: 'optimizer', group: 'Configuration',
    icon: Sliders, primary: true,
    description: 'Presentation, multimedia and responsiveness settings as reversible toggles.',
    keywords: ['tweak', 'windows', 'registry', 'bcd', 'animation', 'transparency', 'responsiveness', 'feature'],
  },
  {
    id: 'registry', label: 'Registry', zone: 'optimizer', group: 'Configuration',
    icon: FileCode,
    description: 'Scan for orphaned and invalid registry entries, with backup and restore.',
    keywords: ['registry', 'regedit', 'orphan', 'mruicache', 'clsid', 'invalid', 'backup', 'hive'],
  },
  {
    id: 'debloat', label: 'Debloater', zone: 'optimizer', group: 'Configuration',
    icon: Trash2, primary: true,
    description: 'Remove preinstalled apps and scheduled tasks you never asked for.',
    keywords: ['debloat', 'bloatware', 'remove app', 'uninstall', 'cortana', 'xbox', 'widgets', 'appx'],
  },
  {
    id: 'security', label: 'Security', zone: 'optimizer', group: 'Safety',
    icon: Shield, primary: true,
    description: 'Firewall state, advertising ID, location tracking and telemetry tasks.',
    keywords: ['security', 'firewall', 'defender', 'telemetry', 'privacy', 'advertising id', 'location', 'hardening'],
  },
  {
    id: 'privacy', label: 'Privacy', zone: 'optimizer', group: 'Safety',
    icon: Users,
    description: 'Disable data collection, activity history and personalised advertising.',
    keywords: ['privacy', 'tracking', 'data collection', 'telemetry', 'cortana', 'activity history', 'tailored'],
  },
  {
    id: 'system-repair', label: 'System Repair', zone: 'optimizer', group: 'Recovery',
    icon: Wrench, primary: true,
    description: 'SFC and DISM scans, disk check, boot time measurement and context menu reset.',
    keywords: ['repair', 'fix', 'sfc', 'dism', 'corrupt', 'chkdsk', 'boot time', 'context menu', 'restore'],
  },
  {
    id: 'scheduler', label: 'Scheduler', zone: 'optimizer', group: 'Automation',
    icon: Calendar,
    description: 'Sets how often maintenance runs automatically in the background.',
    keywords: ['scheduler', 'schedule', 'interval', 'periodic', 'timer', 'automate', 'cron'],
  },
  {
    id: 'automation', label: 'Automation', zone: 'optimizer', group: 'Automation',
    icon: Layers,
    description: 'Build multi-step routines such as daily clean or pre-game optimisation.',
    keywords: ['automation', 'routine', 'workflow', 'macro', 'recipe', 'task', 'sequence'],
  },

  // ---------------------------------------------------------------- monitor
  {
    id: 'live-monitor', label: 'Live Monitor', zone: 'monitor', group: 'Live data',
    icon: LineChart, primary: true,
    description: 'Second-by-second CPU, GPU, RAM, disk, network and temperature graphs.',
    keywords: ['monitor', 'graph', 'chart', 'realtime', 'live', 'watch', 'fps'],
  },

  // ------------------------------------------------------------ diagnostics
  {
    id: 'health-scores', label: 'Health Scores', zone: 'diagnostics', group: 'Start here',
    icon: HeartPulse, primary: true,
    description: 'Scored breakdown of PC, Windows, gaming, storage and security health.',
    keywords: ['score', 'rating', 'grade', 'health', 'benchmark', 'audit'],
  },
  {
    id: 'troubleshooter', label: 'Troubleshooter', zone: 'diagnostics', group: 'Start here',
    icon: Stethoscope, primary: true,
    description: 'Troubleshoot hardware, drivers, network and event log problems.',
    keywords: ['diagnose', 'problem', 'issue', 'troubleshoot', 'check', 'doctor', 'error', 'diagnostics'],
  },
  {
    id: 'device', label: 'Devices', zone: 'diagnostics', group: 'Hardware',
    icon: Info,
    description: 'Device manager view with problem devices and driver status.',
    keywords: ['device', 'device manager', 'hardware id', 'problem device', 'unknown device', 'pnp'],
  },
  {
    id: 'device-info', label: 'Device Info', zone: 'diagnostics', group: 'Hardware',
    icon: Info,
    description: 'Full inventory: CPU, GPU, motherboard, RAM, storage, BIOS and network.',
    keywords: ['device info', 'inventory', 'specs', 'system info', 'hardware id', 'what do i have', 'serial'],
  },
  {
    id: 'drivers', label: 'Drivers', zone: 'diagnostics', group: 'Drivers',
    icon: ScanLine,
    description: 'Enumerate installed drivers with version and provider details.',
    keywords: ['driver', 'drivers', 'version', 'provider', 'inf', 'signed', 'enumerate'],
  },
  {
    id: 'driver-center', label: 'Driver Center', zone: 'diagnostics', group: 'Drivers',
    icon: HeartPulse,
    description: 'Driver health score, vulnerable driver scan, backup and restore.',
    keywords: ['driver health', 'vulnerable', 'outdated driver', 'backup driver', 'driver restore', 'cve'],
  },
  {
    id: 'drivers-update', label: 'Driver Updates', zone: 'diagnostics', group: 'Drivers',
    icon: Download, primary: true,
    description: 'Check for newer driver versions and install them.',
    keywords: ['update driver', 'upgrade', 'new version', 'download driver', 'gpu driver', 'chipset'],
  },
  {
    id: 'software', label: 'Software Updates', zone: 'diagnostics', group: 'Updates',
    icon: Package, primary: true,
    description: 'Find outdated installed applications and update them.',
    keywords: ['software update', 'app update', 'outdated', 'upgrade app', 'program', 'installed apps'],
  },

  /* The reports destination renders ReportsPage directly (it has exactly one
     tool), so there is no separate `reports` tool entry - a tool id equal to
     a destination id would be unreachable, the very bug this IA fixes. */

  // ---------------------------------------------------------------- history
  {
    id: 'timeline', label: 'Timeline', zone: 'history', group: 'History',
    icon: History, primary: true,
    description: 'Every optimization run over time with before and after measurements.',
    keywords: ['timeline', 'history', 'log', 'chronology', 'changes', 'past', 'trend'],
  },
  {
    id: 'notifications', label: 'Notifications', zone: 'history', group: 'History',
    icon: Bell,
    description: 'Alerts raised by the monitor, scheduler and maintenance tasks.',
    keywords: ['alert', 'notification', 'message', 'inbox', 'warning'],
  },
  {
    id: 'rollback', label: 'Rollback', zone: 'history', group: 'History',
    icon: Undo2, primary: true,
    description: 'Restore points and registry snapshots. Undo anything Optinix changed.',
    keywords: ['rollback', 'undo', 'revert', 'restore', 'backup', 'snapshot', 'reset', 'safe'],
  },

  // --------------------------------------------------------- personalization
  {
    id: 'theme', label: 'Appearance', zone: 'personalization', group: 'Preferences',
    icon: Wand,
    description: 'Backgrounds, glass effects and the legacy accent picker.',
    keywords: ['theme', 'appearance', 'accent', 'colour', 'color', 'wallpaper', 'background', 'glass', 'effects'],
  },

  // --------------------------------------------------------------- settings
  {
    id: 'general', label: 'General', zone: 'settings', group: 'Preferences',
    icon: Settings2, primary: true,
    description: 'Startup behaviour, units, update checks and data locations.',
    keywords: ['settings', 'general', 'preferences', 'options', 'config', 'start on boot', 'units'],
  },
  {
    id: 'ai-settings', label: 'AI Settings', zone: 'settings', group: 'AI',
    icon: BrainCircuit,
    description: 'Connect OpenAI, Gemini, Claude, OpenRouter, Ollama or LM Studio.',
    keywords: ['ai', 'openai', 'gpt', 'gemini', 'claude', 'anthropic', 'openrouter', 'ollama', 'lm studio', 'api key', 'model'],
  },
  {
    id: 'toolbox', label: 'Toolbox', zone: 'settings', group: 'Utilities',
    icon: Briefcase,
    description: 'DNS, Defender, Windows Update, Office telemetry and context menu controls.',
    keywords: ['toolbox', 'utility', 'defender toggle', 'windows update toggle', 'office telemetry', 'hpet', 'powershell'],
  },
  {
    id: 'tools-center', label: 'Tools Center', zone: 'settings', group: 'Utilities',
    icon: Boxes,
    description: 'Process manager, hosts file editor, environment variables and Windows features.',
    keywords: ['tools', 'process manager', 'kill process', 'hosts file', 'environment variable', 'windows feature', 'optional feature'],
  },
  {
    id: 'developer', label: 'Developer Tools', zone: 'settings', group: 'Extensions',
    icon: Terminal,
    description: 'Check toolchains and reclaim npm, pip, Docker, git and IDE cache space.',
    keywords: ['developer', 'dev', 'npm', 'pip', 'docker', 'git gc', 'node', 'python', 'ide cache', 'toolchain', 'sdk'],
  },
  {
    id: 'extensions', label: 'Extensions', zone: 'settings', group: 'Extensions',
    icon: Boxes,
    description: 'Optional feature packs such as Hyper-V, WSL and the Windows Subsystem.',
    keywords: ['extension', 'feature', 'optional', 'hyper-v', 'wsl', 'subsystem', 'linux', 'container'],
  },
  {
    id: 'plugins', label: 'Plugins', zone: 'settings', group: 'Extensions',
    icon: Puzzle,
    description: 'Install and manage third-party optimizers through the plugin API.',
    keywords: ['plugin', 'extension', 'addon', 'module', 'developer api', 'sample plugin'],
  },
  {
    id: 'marketplace', label: 'Marketplace', zone: 'settings', group: 'Extensions',
    icon: Store,
    description: 'Ready-made tuning packs for OBS, Blender, Unity, Steam and more.',
    keywords: ['marketplace', 'store', 'pack', 'bundle', 'obs', 'blender', 'unity', 'unreal', 'steam', 'minecraft'],
  },
]

export const TOOL_MAP: Record<string, Tool> = Object.fromEntries(TOOLS.map((t) => [t.id, t]))

export const PRIMARY_TOOLS = TOOLS.filter((t) => t.primary)

export function toolsInZone(zone: ZoneId): Tool[] {
  const inZone = TOOLS.filter((t) => t.zone === zone)
  const primaries = inZone.filter((t) => t.primary)
  const rest = inZone.filter((t) => !t.primary)
  return [...primaries, ...rest]
}

export function groupsInZone(zone: ZoneId): string[] {
  const seen: string[] = []
  for (const t of TOOLS) {
    if (t.zone === zone && !seen.includes(t.group)) seen.push(t.group)
  }
  return seen
}

export function zoneForTool(toolId: string): ZoneId | undefined {
  return TOOL_MAP[toolId]?.zone
}

/* ------------------------------------------------------------------ search */

/** Pre-lowercased haystack per tool, built once at module load. */
const HAYSTACKS = new Map<string, string>(
  TOOLS.map((t) => [
    t.id,
    [t.label, t.description, t.group, t.keywords.join(' '), ZONE_MAP[t.zone].label]
      .join(' ')
      .toLowerCase(),
  ]),
)

/**
 * Subsequence match with contiguity and word-start bonuses.
 * Returns a score where higher is better, or -1 when the query does not match.
 */
export function fuzzyScore(toolId: string, query: string): number {
  if (!query) return 0
  const hay = HAYSTACKS.get(toolId)
  if (!hay) return -1

  const label = TOOL_MAP[toolId].label.toLowerCase()
  if (label === query) return 1000
  if (label.startsWith(query)) return 900 - label.length
  if (label.includes(query)) return 800 - label.indexOf(query)
  if (hay.includes(query)) return 600 - hay.indexOf(query) * 0.1

  // Subsequence fallback so "mnyfr" still reaches Memory Optimizer.
  let score = 0
  let hi = 0
  let streak = 0
  for (const ch of query) {
    if (ch === ' ') continue
    const found = hay.indexOf(ch, hi)
    if (found === -1) return -1
    streak = found === hi ? streak + 1 : 0
    score += 10 + streak * 6 - Math.min(found - hi, 12)
    if (found === 0 || hay[found - 1] === ' ') score += 14
    hi = found + 1
  }
  return Math.max(1, score)
}

export function searchTools(query: string, limit = 40): Tool[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  return TOOLS
    .map((t) => ({ tool: t, score: fuzzyScore(t.id, q) }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((r) => r.tool)
}
