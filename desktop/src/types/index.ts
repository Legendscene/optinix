export interface SystemInfo {
  cpu: { percent: number; logical: number; physical: number; temperature: number | null }
  memory: { percent: number; total_gb: number; used_gb: number; available_gb: number }
  disk: DiskInfo[]
  network: { bytes_sent: number; bytes_recv: number; speed_up: number; speed_down: number }
  gpu: GpuInfo
  system: { os: string; processor: string; uptime: string }
  os: { os_name: string; release: string }
}

export interface DiskInfo {
  device: string; mountpoint: string; fstype: string
  total: number; used: number; free: number; percent: number
  is_external?: boolean; is_ssd?: boolean | null
}

export interface GpuInfo {
  name: string; usage: number; memory_total: number
  memory_used: number; temperature: number; driver: string
}

export interface Service { name: string; desc: string; running: boolean; safe: boolean }
export interface StartupApp { name: string; desc: string }
export interface DriverInfo { name: string; manufacturer?: string; version?: string; download_url?: string }

export interface SmartDetect {
  hardware: Record<string, string>
  recommendations: { type: string; priority: string; message: string }[]
}

export interface TweakState { [key: string]: boolean }
export interface NetworkAdapter { name: string; description: string; speed: string; enabled: boolean }

export interface HealthScore {
  score: number
  label: string
  color: string
}

export interface AiHealthScoreResponse {
  score: number
  label: string
  color: string
  components: { cpu: number; memory: number; disk: number; system: number; security: number; performance: number }
  details: Record<string, unknown>
}

export interface AiRecommendation {
  type: string
  priority: string
  title: string
  description: string
  benefit: string
  risk: string
  category: string
}

export interface AiRecommendationsResponse {
  recommendations: AiRecommendation[]
  count: number
}

export interface AiBottleneck {
  type: string
  severity: string
  description: string
  recommendation: string
}

export interface AiBottlenecksResponse {
  bottlenecks: AiBottleneck[]
  count: number
}

export interface HardwareInfo {
  cpu: { vendor: string; physical_cores: number; logical_cores: number; brand: string }
  gpu: { vendor: string }
  ram: { total_gb: number; available_gb: number; used_gb: number; percent: number }
  disk: { is_ssd: boolean; is_hdd: boolean; type: string }
  system: {
    is_laptop: boolean
    is_vm: boolean
    is_admin: boolean
    os: { release: string; version: string; build: string; is_win11: boolean; is_win10: boolean; product: string }
  }
  power_plan: { guid: string; name: string; is_high_performance: boolean }
  security: { secure_boot: boolean | null; tpm: { present: boolean; enabled: boolean } }
}

export interface OptimizationEntry {
  id: string
  name: string
  category: string
  description: string
  benefit: string
  risks: string
  admin_required: boolean
  compatibility?: Record<string, unknown>
}

export interface CompatibilityCheck {
  compatible: boolean
  category: string
  compatibility: Record<string, string>
  failures: Record<string, string>
  passes: Record<string, string>
  admin_required: boolean
  risks: string
  description: string
}

export interface HealthScoreEntry {
  score: number
  label: string
  details: Record<string, unknown>
}

export interface HealthScoresResponse {
  pc_health: HealthScoreEntry
  windows_health: HealthScoreEntry
  gaming: HealthScoreEntry
  developer: HealthScoreEntry
  security: HealthScoreEntry
  storage: HealthScoreEntry
  battery: HealthScoreEntry
  overall: number
  timestamp: string
}

export interface MonitorMetrics {
  cpu: number
  ram: number
  ram_used_gb: number
  ram_total_gb: number
  disk_read_mbs: number
  disk_write_mbs: number
  disk_usage_percent: number
  gpu: number | null
  gpu_temp: number | null
  gpu_memory_used: number | null
  network_sent_mbs: number
  network_recv_mbs: number
  battery: number | null
  battery_power_plugged: boolean | null
  processes: number
  temperature: number | null
}

/**
 * Raw payload of GET /api/monitor/current: an envelope around one live sample.
 * The backend uses its own field names (disk_read, network_download…), which
 * api.monitorCurrent flattens into MonitorMetrics. Fields may be null when a
 * sensor is unavailable — null means "unknown", never zero.
 */
export interface MonitorCurrentResponse {
  snapshot: {
    cpu?: number | null
    ram?: number | null
    ram_used_gb?: number | null
    ram_total_gb?: number | null
    disk_read?: number | null
    disk_write?: number | null
    disk_usage_percent?: number | null
    gpu?: number | null
    gpu_temp?: number | null
    gpu_memory_used?: number | null
    network_download?: number | null
    network_upload?: number | null
    battery?: number | null
    battery_power_plugged?: boolean | null
    processes?: number | null
    temperature?: number | null
  }
  /** Latest pushed samples per metric from the metrics store (may be empty). */
  latest_tracking?: Record<string, number | null>
}

/**
 * A single metrics snapshot from GET /api/monitor/current. The backend sends
 * no per-sample timestamp, so consumers label live chart points with client
 * receipt time. History points below do carry a server timestamp (epoch s).
 */
export interface MonitorHistoryPoint {
  timestamp: number
  value: number
}

/** Response wrapper from GET /api/monitor/history/<category>. */
export interface MonitorHistoryResponse {
  category: string
  period: string
  count: number
  entries: MonitorHistoryPoint[]
}

export interface DiagnosticsResult {
  status: 'good' | 'warning' | 'critical'
  summary: string
  details: { source: string; message: string; severity?: string }[]
  issues_count: number
}

export interface DiagnosticsSummary {
  total_issues: number
  critical: number
  warnings: number
  good: number
  results: Record<string, DiagnosticsResult>
}

export interface ReportInfo {
  report_id: string
  type: string
  format: string
  timestamp: string
  size: number
}

export interface NotificationItem {
  id: string
  type: string
  title: string
  message: string
  severity: string
  timestamp: number
  read: boolean
  dismissed: boolean
  action?: string
}

export interface TimelineEvent {
  timestamp: number
  type: string
  name: string
  details: string
  benchmark_before?: Record<string, unknown>
  benchmark_after?: Record<string, unknown>
}

/** Shape of GET /api/timeline/summary (TimelineStore.get_timeline_summary). */
export interface TimelineSummary {
  total_metrics: number
  total_events: number
  total_health_scores: number
  events_by_type: Record<string, number>
  average_cpu_percent: number
  average_ram_percent: number
  latest_metrics: Record<string, unknown>
  retention_days: number
}

export interface StorageScanResult {
  drive: string
  total_size: number
  free_space: number
  used_space: number
  scan_time_ms: number
  scanning: boolean
  /** True when the folder budget was hit, so the tree is a partial view. */
  truncated?: boolean
  folder_limit?: number
  tree?: StorageNode
  largest_files?: { path: string; size: number; extension: string }[]
  largest_folders?: { path: string; size: number }[]
  file_type_chart?: Record<string, { size: number; count: number; color: string }>
}

export interface StorageNode {
  path: string
  name: string
  size: number
  is_dir: boolean
  file_count?: number
  folder_count?: number
  children?: StorageNode[]
  percentage?: number
  category?: string
  category_color?: string
}

export interface DeviceInfo {
  cpu: Record<string, unknown>
  gpu: Record<string, unknown>
  motherboard: Record<string, unknown>
  ram: Record<string, unknown>
  storage: Record<string, unknown>
  battery: Record<string, unknown>
  network: Record<string, unknown>
  bios: Record<string, unknown>
  drivers: Record<string, unknown>
}

export interface MarketplaceModule {
  id: string
  name: string
  description: string
  version: string
  category: string
  icon: string
  installed: boolean
  install_time?: string
  tags?: string[]
  downloads?: number
}

export interface MaintenanceTask {
  id: string
  name: string
  type: 'daily' | 'weekly' | 'monthly'
  actions: string[]
  enabled: boolean
  last_run: string | null
  next_run: string | null
  created_at: string
}

export interface AIProvider {
  name: string
  available: boolean
  configured: boolean
  models: string[]
  type: string
}

/* ------------------------------------------------- Overview / home screen */

export interface OverviewHealth {
  overall: number
  scores: Record<string, { score: number; label: string }>
}

export interface OverviewGpu {
  name: string
  usage: number | null
  temperature: number | null
  memory_used: number
  memory_total: number
}

export interface OverviewVitals {
  cpu_percent: number
  cpu_temp: number | null
  cpu_threads: number
  cpu_cores: number
  ram_percent: number
  ram_used_gb: number
  ram_total_gb: number
  ram_available_gb: number
  swap_percent: number
  disk_percent: number
  disk_free_gb: number
  disk_total_gb: number
  process_count: number
  network_down_kbs: number
  network_up_kbs: number
  uptime_hours: number
  gpu: OverviewGpu
  power_plan: { name: string; is_high_performance: boolean }
  is_laptop: boolean
  battery: { percent: number; plugged: boolean; seconds_left: number | null } | null
  is_admin: boolean
  detected_game: string | null
}

export interface OverviewAction {
  id: string
  title: string
  detail: string
  severity: 'high' | 'medium' | 'low' | 'ok'
  /** Route to open when the user acts on this. */
  page: string
  /** Optional in-page action id the target page understands. */
  action: string | null
  meta: Record<string, unknown>
}

export interface OverviewReclaimable {
  total_bytes: number
  categories: { name: string; bytes: number; file_count: number }[]
}

export interface HistoryBenchmark {
  before: Record<string, number>
  after: Record<string, number>
  comparison: Record<string, { improved: boolean; delta: number; percent: number }>
}

export interface OverviewLastOptimization {
  entry_id: string
  category: string
  name: string
  timestamp: string
  duration_ms: number
  success_count: number
  total_count: number
  error: string | null
  benchmark_before: Record<string, number> | null
  benchmark_after: Record<string, number> | null
  benchmark_comparison: Record<string, { improved: boolean; delta: number; percent: number }> | null
}

export interface DetectedGame {
  id: string
  name: string
  description: string
}

export interface Overview {
  generated_at: number
  is_admin: boolean
  health: OverviewHealth
  vitals: OverviewVitals
  detected_game: DetectedGame | null
  actions: OverviewAction[]
  reclaimable: OverviewReclaimable | null
  last_optimization: OverviewLastOptimization | null
}

/* ---------------------------------------------------- Presets / quick run */

export interface PresetMode {
  id: string
  name: string
  summary: string
  /** Exactly what will be changed, shown before applying. */
  detail: string[]
  categories: string[]
  post: string[]
}

export interface Measurement {
  ram_percent: number
  ram_used_gb: number
  ram_available_gb: number
  process_count: number
  disk_free_gb: number
  cpu_percent: number
  timestamp: number
}

export interface OptimizeStep {
  id: string
  label: string
  success: boolean
  message: string
  duration_ms: number
}

export interface OptimizeRun {
  preset: string
  name: string
  is_admin: boolean
  steps: OptimizeStep[]
  succeeded: number
  total: number
  before: Measurement
  after: Measurement
  deltas: {
    ram_used_gb: number
    ram_available_gb: number
    process_count: number
    disk_free_gb: number
  }
}

/* ------------------------------------------------------------ Game profile */

export interface GameProfileSummary {
  id: string
  name: string
  description: string
  builtin: boolean
}

/* ------------------------------------------------------------ Game library */

/* A verified installed game from the backend discovery scan. Statuses are
   produced by validation (launcher record + existing files), never by a
   name lookup. 'missing' = stale launcher record (files gone);
   'restricted' = source could not be inspected (permissions). */
export type GameInstallStatus = 'installed' | 'running' | 'missing' | 'restricted'

export interface DiscoveredGame {
  /** Stable id — '<source>:<native key>', deduplicated across sources. */
  id: string
  name: string
  source: 'steam' | 'epic' | 'riot' | 'battlenet' | 'gog' | 'ea' | 'ubisoft' | 'xbox' | 'registry' | 'custom' | 'gryphline' | 'startmenu' | 'manual'
  install_path: string | null
  exe_path: string | null
  status: GameInstallStatus
  /** Steam appid for cover art, when the source provides one. */
  appid?: number
  /** Epoch seconds of the scan that last verified this record. */
  last_verified?: number
  profile_id?: string
  /* gryphline launcher exe (Launcher.exe) for games without a direct exe */
  launcher_exe?: string | null
  /* sources merged into one record (steam + registry etc.) */
  sources?: string[]
  /* manual merge tag — 'manually added' */
  label?: string
  args?: string
  /** Discovery kind: 'emulator' marks a discovered emulator shell so the
      library can keep it separate from native PC games. */
  kind?: 'game' | 'emulator'
  /** Explainable discovery evidence (folder scanner records). */
  evidence?: string
  emulator_id?: string | null
  emulator?: EmulatorEntry | null
}

export interface GameLibrary {
  games: DiscoveredGame[]
  notes: string[]
  scanned_at: number | null
  needs_scan: boolean
  error?: string | null
  cancelled?: boolean
  /** Per-source scan diagnostics; absent on pre-first-scan payloads. */
  diagnostics?: ScanDiagnostics | null
}

/** Honest per-source scan summary — what was inspected and why nothing was found. */
export interface ScanDiagnostics {
  sources: {
    source: string
    label: string
    /** inspected | not_installed | access_restricted | error */
    status: string
    games: number
    notes: string[]
  }[]
  candidates_found: number
  verified_installed: number
  duplicates_removed: number
  inaccessible: number
}

/* One game's live session from GET /api/game-library/session:<id>.
   Null = genuinely unavailable — the UI shows an em dash, never a fake 0. */
export interface GameSessionData {
  game: DiscoveredGame
  session: {
    running: boolean
    started_at: number | null
    duration_s: number | null
    game_cpu_pct: number | null
    game_ram_mb: number | null
  }
  /** Whole-system metrics from the existing monitor engine (per-game CPU/RAM
      comes separately in `session` when process attribution is supported). */
  system_metrics: Record<string, unknown>
  profile: { id: string; name: string | null } | null
  now: number
}

/* ---- Gaming Center V2: manual imports & emulators ----
   A manual entry is whatever the user picked themselves — it is NEVER
   presented as launcher-discovered. status is re-verified live each read. */
export type ManualSource = 'manual'

export interface EmulatorEntry {
  id: string
  name: string
  exe_path: string
  args: string
  added_at: number
}

export interface ManualGameEntry {
  id: string
  name: string
  exe_path: string
  args: string
  workdir?: string
  folder?: string
  source: ManualSource
  added_at: number
  emulator_id?: string | null
  /* present on list/read responses, not in the stored JSON */
  status?: 'installed' | 'missing'
  emulator?: EmulatorEntry | null
  label?: string
}

export interface ManualLibrary {
  games: ManualGameEntry[]
  emulators: EmulatorEntry[]
}

export interface GameExeCandidate {
  path: string
  name: string
  size_mb: number
}

export interface GameScanProgress {
  running: boolean
  fraction: number
  games_found: number
  cancel_requested: boolean
  error?: string | null
}

/* What the installed-games scan returns: evidence about games actually on this
   PC, never an invented list. matched -> profile exists; others -> installed
   but no optimization profile for it yet. */
export interface InstalledGamesSet {
  matched: { profile_id: string; source: string; appid?: number }[]
  others: { name: string; source: string; appid?: number }[]
}

export interface PingResult {
  host: string
  avg_ms?: number
  min_ms?: number
  max_ms?: number
  packet_loss?: number
  samples?: number
  error?: string
}

/* ------------------------------------------------ Network Intelligence ---
 * Real measurements only. A probe that cannot reach its target returns
 * ok:false with an explanation, which the UI renders as an unavailable state.
 * There is no fabricated value and no routing/multipath claim: Optinix has no
 * relay infrastructure, so these are diagnostics, not traffic control.
 */

export interface NetworkLatency {
  ok: boolean
  host: string
  /** Round-trip statistics in milliseconds; absent when no reply arrived. */
  avg_ms?: number | null
  min_ms?: number | null
  max_ms?: number | null
  /** Population standard deviation of round-trip times. */
  jitter_ms?: number | null
  /** Percentage of sent probes with no reply. */
  packet_loss_pct?: number | null
  sent?: number
  received?: number
  /** True when replies were faster than ping's reporting resolution. */
  sub_ms?: boolean
  samples_ms?: number[]
  error?: string
}

export interface NetworkDnsResolve {
  ok: boolean
  host: string
  addresses?: string[]
  resolve_ms?: number
  error?: string
}

export interface NetworkMethodology {
  jitter: string
  packet_loss: string
  routing_note: string
}

export interface NetworkAnalyzeResult {
  target: string
  latency: NetworkLatency
  dns: NetworkDnsResolve
  /** Epoch seconds. */
  timestamp: number
  methodology: NetworkMethodology
}

export interface TraceHop {
  ip: string
  ok: boolean
  avg_ms?: number
  times_ms?: number[]
}

export interface NetworkTraceResult {
  ok: boolean
  host: string
  hops: TraceHop[]
  error?: string
}

export interface NetworkTarget {
  id: string
  label: string
  host: string
  note: string
}

export interface NetworkDnsServers {
  ok: boolean
  servers: string[]
  error?: string
}

export interface GameProfile {
  name: string
  description: string
  process_keywords?: string[]
  power_plan?: string
  cpu_affinity?: number[] | 'all'
  gpu_priority?: string
  process_priority?: string
  network_tweaks?: Record<string, unknown>
  [key: string]: unknown
}
