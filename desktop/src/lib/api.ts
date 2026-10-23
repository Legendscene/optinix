const BASE = ''

/** Most reads are cheap, but a few aggregates scan the whole disk. */
const READ_TIMEOUT = 15000
const WRITE_TIMEOUT = 30000
/**
 * Optimization runs block until the OS work finishes. A category takes a few
 * seconds, "all" can take minutes, so those endpoints get a much longer budget
 * than the default or the request is aborted while the tweak is still applied.
 */
const LONG_TIMEOUT = 480000

async function get<T>(path: string, timeout = READ_TIMEOUT): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { signal: AbortSignal.timeout(timeout) })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

async function post<T>(path: string, body?: unknown, timeout = WRITE_TIMEOUT): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeout),
  })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

async function patch<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000),
  })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

async function put<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000),
  })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

async function del<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'DELETE',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000),
  })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

export const api = {
  // ---- Intelligence / Health Scores ----
  healthScores: () => get<import('../types').HealthScoresResponse>('/api/intelligence/scores'),
  healthScoreOverall: () => get<{ score: number }>('/api/intelligence/overall'),

  // ---- Live Monitor ----
  monitorCurrent: async () => {
    // The endpoint wraps the sample in {snapshot, latest_tracking} and names
    // some fields differently (disk_read vs disk_read_mbs). Flatten it here so
    // pages consume one stable shape. Nulls pass through as null — unavailable
    // sensors must not render as 0.
    const res = await get<import('../types').MonitorCurrentResponse>('/api/monitor/current')
    const s = res.snapshot ?? {}
    const m: import('../types').MonitorMetrics = {
      cpu: s.cpu ?? 0,
      ram: s.ram ?? 0,
      ram_used_gb: s.ram_used_gb ?? 0,
      ram_total_gb: s.ram_total_gb ?? 0,
      disk_read_mbs: s.disk_read ?? 0,
      disk_write_mbs: s.disk_write ?? 0,
      disk_usage_percent: s.disk_usage_percent ?? 0,
      gpu: s.gpu ?? null,
      gpu_temp: s.gpu_temp ?? null,
      gpu_memory_used: s.gpu_memory_used ?? null,
      network_sent_mbs: s.network_upload ?? 0,
      network_recv_mbs: s.network_download ?? 0,
      battery: s.battery ?? null,
      battery_power_plugged: s.battery_power_plugged ?? null,
      processes: s.processes ?? 0,
      temperature: s.temperature ?? null,
    }
    return m
  },
  monitorHistory: (category: string, period = '1h') => get<import('../types').MonitorHistoryResponse>(`/api/monitor/history/${category}?period=${period}`),
  monitorStatus: () => get<{ running: boolean; uptime: number }>('/api/monitor/status'),
  monitorStart: () => post('/api/monitor/start'),
  monitorStop: () => post('/api/monitor/stop'),

  // ---- Diagnostics ----
  diagnosticsAll: () => get<Record<string, import('../types').DiagnosticsResult>>('/api/diagnostics/all'),
  diagnosticsSummary: () => get<import('../types').DiagnosticsSummary>('/api/diagnostics/summary'),
  diagnosticsCategory: (cat: string) => get<import('../types').DiagnosticsResult>(`/api/diagnostics/${cat}`),

  // ---- Maintenance ----
  maintenanceTasks: () => get<{ tasks: import('../types').MaintenanceTask[] }>('/api/maintenance/tasks'),
  maintenanceCreateTask: (task: Partial<import('../types').MaintenanceTask>) => post('/api/maintenance/tasks', task),
  maintenanceUpdateTask: (id: string, task: Partial<import('../types').MaintenanceTask>) => put(`/api/maintenance/tasks/${id}`, task),
  maintenanceDeleteTask: (id: string) => del(`/api/maintenance/tasks/${id}`),
  maintenanceRunTask: (id: string) => post(`/api/maintenance/tasks/${id}/run`),
  maintenanceRunAll: () => post('/api/maintenance/run'),
  maintenanceStatus: () => get('/api/maintenance/status'),
  maintenanceHistory: () => get('/api/maintenance/history'),

  // ---- Reports ----
  reportsGenerate: (type: string, format = 'html') => post<{ report_id: string; path: string }>('/api/reports/generate', { type, format }),
  reportsList: (type?: string) => get<{ reports: import('../types').ReportInfo[] }>(`/api/reports${type ? `?type=${type}` : ''}`),
  reportsGet: (id: string) => get(`/api/reports/${id}`),
  reportsDelete: (id: string) => del(`/api/reports/${id}`),
  reportsTypes: () => get<{ types: string[] }>('/api/reports/types'),

  // ---- Notifications ----
  notificationsList: (includeDismissed = false) => get<{ notifications: import('../types').NotificationItem[] }>(`/api/notifications?include_dismissed=${includeDismissed}`),
  notificationsUnread: () => get<{ count: number }>('/api/notifications/unread-count'),
  notificationsMarkRead: (id: string) => put(`/api/notifications/${id}/read`),
  notificationsMarkAllRead: () => put('/api/notifications/read-all'),
  notificationsDismiss: (id: string) => put(`/api/notifications/${id}/dismiss`),
  notificationsDismissAll: () => put('/api/notifications/dismiss-all'),
  notificationsRecent: () => get<{ notifications: import('../types').NotificationItem[] }>('/api/notifications/recent'),

  // ---- Timeline ----
  timelineMetrics: (metric: string, hours = 24) => get(`/api/timeline/metrics/${metric}?hours=${hours}`),
  timelineEvents: (limit = 50) => get<{ events: import('../types').TimelineEvent[] }>(`/api/timeline/events?limit=${limit}`),
  timelineHealthScores: (days = 7) => get(`/api/timeline/health-scores?days=${days}`),
  timelineSummary: () => get<import('../types').TimelineSummary>('/api/timeline/summary'),
  timelineOptimizationImpact: () => get('/api/timeline/optimization-impact'),
  timelineBootTimes: (days = 7) => get(`/api/timeline/boot-times?days=${days}`),

  // ---- Storage Visualizer ----
  storageScan: (drive = 'C:\\') => post<{ scanning: boolean }>('/api/storage/scan', { drive }),
  storageScanStatus: () => get<{ scanning: boolean }>('/api/storage/scan-status'),
  storageResults: () => get<import('../types').StorageScanResult>('/api/storage/results'),
  storageCancelScan: () => post('/api/storage/cancel-scan'),
  storageDriveInfo: () => get('/api/storage/drive-info'),

  // ---- Device Info ----
  deviceInfo: (category?: string) => get<import('../types').DeviceInfo>(category ? `/api/device-info/${category}` : '/api/device-info/all'),
  deviceSummary: () => get<Record<string, string>>('/api/device-info/summary'),

  // ---- Tools Center ----
  toolsEnvList: (scope = 'both') => get(`/api/tools/env?scope=${scope}`),
  toolsEnvGet: (name: string) => get(`/api/tools/env/${encodeURIComponent(name)}`),
  toolsEnvSet: (name: string, value: string, scope = 'user') => post('/api/tools/env', { name, value, scope }),
  toolsEnvDelete: (name: string, scope = 'user') => del(`/api/tools/env/${encodeURIComponent(name)}?scope=${scope}`),
  toolsHostsGet: () => get('/api/tools/hosts'),
  toolsHostsAdd: (ip: string, hostname: string, comment = '') => post('/api/tools/hosts', { ip, hostname, comment }),
  toolsHostsRemove: (line: number) => del(`/api/tools/hosts/${line}`),
  toolsHostsToggle: (line: number) => put(`/api/tools/hosts/${line}/toggle`),
  toolsLaunch: (tool: string) => post(`/api/tools/launch/${tool}`),
  toolsProcesses: (sort = 'memory', limit = 50) => get(`/api/tools/processes?sort_by=${sort}&limit=${limit}`),
  toolsProcessKill: (pid: number) => del(`/api/tools/processes/${pid}`),
  toolsWindowsFeatures: () => get('/api/tools/windows-features'),
  toolsFeatureEnable: (name: string) => post(`/api/tools/windows-features/${encodeURIComponent(name)}/enable`),
  toolsFeatureDisable: (name: string) => post(`/api/tools/windows-features/${encodeURIComponent(name)}/disable`),
  toolsFlushDns: () => post('/api/tools/network/flush-dns'),
  toolsResetWinsock: () => post('/api/tools/network/reset-winsock'),

  // ---- Marketplace ----
  marketplaceModules: (category?: string) => get<{ modules: import('../types').MarketplaceModule[] }>(`/api/marketplace/modules${category ? `?category=${category}` : ''}`),
  marketplaceModule: (id: string) => get<import('../types').MarketplaceModule>(`/api/marketplace/modules/${id}`),
  marketplaceCategories: () => get<{ categories: string[] }>('/api/marketplace/categories'),
  marketplaceInstall: (id: string) => post(`/api/marketplace/modules/${id}/install`),
  marketplaceUninstall: (id: string) => post(`/api/marketplace/modules/${id}/uninstall`),

  // ---- AI Provider ----
  aiProviders: () => get<{ providers: import('../types').AIProvider[] }>('/api/ai/providers'),
  aiSetProvider: (name: string) => post('/api/ai/provider/set', { name }),
  aiConfigureProvider: (name: string, config: Record<string, string>) => post('/api/ai/provider/configure', { name, ...config }),
  aiChat: (messages: { role: string; content: string }[]) => post('/api/ai/chat', { messages }),

  systemInfo: () => get<import('../types').SystemInfo>('/api/system-info'),
  services: () => get<{ services: import('../types').Service[] }>('/api/services'),
  toggleService: (name: string, enable: boolean) => post('/api/services/toggle', { name, enable }),
  startup: () => get<{ apps: import('../types').StartupApp[] }>('/api/startup'),
  toggleStartup: (name: string, enable: boolean) => post('/api/startup/toggle', { name, enable }),
  externalDisks: () => get<{ disks: import('../types').DiskInfo[] }>('/api/external-disk'),
  smartDetect: () => get<import('../types').SmartDetect>('/api/smart-detect'),
  tweakState: () => get<import('../types').TweakState>('/api/tweak-state'),
  tweakStateSet: (kv: Record<string, boolean>) => post<{ success: boolean }>('/api/tweak-state/set', kv),
  ramBoost: () => post<{ success: boolean; message: string }>('/api/ram-boost'),
  networkAdapters: () => get<{ adapters: import('../types').NetworkAdapter[] }>('/api/network/adapters'),
  drivers: () => get<{ drivers: import('../types').DriverInfo[] }>('/api/drivers/scan'),
  schedulerStatus: () => get<{ enabled: boolean; interval_hours: number }>('/api/scheduler/status'),
  optimize: (cat: string) => post<unknown>(`/api/optimize/${cat}`, undefined, LONG_TIMEOUT),
  optimizeAll: () => post<Record<string, unknown>>('/api/optimize/all', undefined, LONG_TIMEOUT),
  extreme: () => post<{ results: unknown[] }>('/api/tuning/extreme'),
  tuneAdapter: (adapter: string, preset: string) => post('/api/network/tune-adapter', { adapter, preset }),
  bufferbloat: (preset: string) => post('/api/network/bufferbloat', { preset }),
  qos: (enable: boolean) => post('/api/network/qos', { enable }),
  advancedNetwork: () => post('/api/network/advanced-tweaks'),
  gpuOptimize: () => post('/api/optimize/gpu'),
  peripheralOptimize: () => post('/api/optimize/peripheral'),
  affinityOptimize: () => post('/api/optimize/affinity'),
  debloat: (preset: 'basic' | 'advanced') => post('/api/services/debloat', { preset }),
  dns: (provider: string) => post('/api/toolbox/dns', { provider }),
  flushDns: () => post('/api/toolbox/flush-dns'),
  ping: (host = '8.8.8.8') => post<{ output: string }>('/api/toolbox/ping', { host }),
  toggleWindowsUpdate: (enable: boolean) => post('/api/toolbox/windows-update', { enable }),
  toggleDefender: (enable: boolean) => post('/api/toolbox/defender', { enable }),
  toggleContextMenu: (enable: boolean) => post('/api/toolbox/context-menu', { enable }),
  setPowerPlan: (plan: string) => post('/api/toolbox/power-plan', { plan }),
  disableOfficeTelemetry: () => post('/api/toolbox/office-telemetry'),
  disableHpet: () => post('/api/toolbox/hpet'),
  hardwareInfo: () => get<{ info: Record<string, string> }>('/api/toolbox/hardware'),
  missingDrivers: () => get<{ missing: string[] }>('/api/drivers/missing'),
  backgroundStatus: () => get<{ running: boolean }>('/api/background/status'),
  backgroundStart: () => post('/api/background/start'),
  backgroundStop: () => post('/api/background/stop'),

  // BIOS
  biosInfo: () => get<{ motherboard: Record<string, string>; bios_vendor: string }>('/api/bios/info'),
  biosRecommendations: () => get<{ recommendations: { name: string; setting: string; description: string }[] }>('/api/bios/recommendations'),
  biosApply: (settings: unknown[]) => post('/api/bios/apply', { settings }),

  // Game Mode
  gameModeStatus: () => get<{ active: boolean; game_count: number }>('/api/game-mode/status'),
  gameModeGames: () => get<{ games: { pid: number; name: string; cpu_percent: number }[] }>('/api/game-mode/games'),
  gameModeEnable: () => post('/api/game-mode/enable'),
  gameModeDisable: () => post('/api/game-mode/disable'),
  gameModeAffinity: (pid?: number) => post('/api/game-mode/affinity', { pid }),
  gameModeCoreParking: () => post('/api/game-mode/core-parking'),
  gameModeTimerResolution: (ms: number) => post('/api/game-mode/timer-resolution', { resolution_ms: ms }),
  gameModeTimerRestore: () => post('/api/game-mode/timer-restore'),

  // Debloater
  debloatCategories: () => get<{ categories: Record<string, { name: string; description: string; risk: string }> }>('/api/debloat/categories'),
  debloatApply: (category: string, dryRun?: boolean) => post('/api/debloat/apply', { category, dry_run: dryRun }),
  debloatApplyMultiple: (categories: string[], dryRun?: boolean) => post('/api/debloat/apply-multiple', { categories, dry_run: dryRun }),
  debloatRestorePoint: () => post('/api/debloat/restore-point'),
  debloatAppOptimize: (app: string) => post('/api/debloat/app-optimize', { app }),

  // Disk Analyzer
  diskScan: (drive = 'C:') => post<{ categories: { name: string; description: string; items: number; bytes: number; files: { path: string; size: number }[] }[]; total_bytes: number; drive: string }>('/api/disk/scan', { drive }),
  diskCleanCategory: (category: string, drive = 'C:') => post('/api/disk/clean-category', { category, drive }),
  diskCleanAll: (drive = 'C:') => post('/api/disk/clean-all', { drive }),

  // Memory Manager
  memoryProcesses: () => get<{ processes: { pid: number; name: string; rss_mb: number; vms_mb: number; memory_percent: number; cpu_percent: number; status: string }[] }>('/api/memory/processes'),
  memoryFree: () => post('/api/memory/free'),
  memoryAutoOptimize: () => post('/api/memory/auto-optimize'),
  memoryInfo: () => get<{ total_gb: number; available_gb: number; used_gb: number; percent: number; swap_total_gb: number; swap_used_gb: number; swap_percent: number }>('/api/memory/info'),

  // Network Priority
  networkPriorityQosEnable: () => post('/api/network-priority/qos/enable'),
  networkPriorityQosDisable: () => post('/api/network-priority/qos/disable'),
  networkPriorityQosGameTraffic: (exe: string) => post('/api/network-priority/qos/game-traffic', { game_exe: exe }),
  networkPriorityBufferbloatPresets: () => get<{ presets: Record<string, { name: string; description: string }> }>('/api/network-priority/bufferbloat/presets'),
  networkPriorityBufferbloatApply: (preset: string) => post('/api/network-priority/bufferbloat/apply', { preset }),
  networkPriorityAdapterOptimize: (adapter: string, preset: string) => post('/api/network-priority/adapter/optimize', { adapter, preset }),
  networkPriorityAdapterReset: (adapter: string) => post('/api/network-priority/adapter/reset', { adapter }),

  // ---- Network Intelligence (real measurements; no fabricated values) ----
  networkTargets: () => get<{ targets: import('../types').NetworkTarget[] }>('/api/network/targets'),
  networkDnsServers: () => get<import('../types').NetworkDnsServers>('/api/network/dns-servers'),
  networkAnalyze: (host: string, count = 10) =>
    // A ping sweep takes a few seconds; keep it under the read timeout.
    post<import('../types').NetworkAnalyzeResult>('/api/network/analyze', { host, count }, 20000),
  networkTrace: (host: string, maxHops = 30) =>
    // traceroute can take a while per hop, so give it a longer budget.
    post<import('../types').NetworkTraceResult>('/api/network/trace', { host, max_hops: maxHops }, 60000),

  // Registry
  registryScan: () => get<{ issues: { path: string; type: string; name: string; severity: string; description: string; fixable: boolean }[]; total: number }>('/api/registry/scan'),
  registryFix: (paths: string[]) => post<{ success: boolean; results: { success: boolean; message: string }[] }>('/api/registry/fix', { paths }),
  registryBackup: () => post<{ success: boolean; message: string; backups: { name: string; size: number; created: string }[] }>('/api/registry/backup'),
  registryRestore: (filename: string) => post<{ success: boolean; message: string }>('/api/registry/restore', { filename }),
  registryBackups: () => get<{ backups: { name: string; size: number; created: string }[] }>('/api/registry/backups'),

  // Windows Tweaks
  tweaksList: () => get<{ tweaks: Record<string, { path: string; name: string; type: string; on: string; off: string }>; categories: Record<string, string[]> }>('/api/tweaks/list'),
  tweaksApply: (tweak: string, enable: boolean) => post('/api/tweaks/apply', { tweak, enable }),
  tweaksApplyMultiple: (tweaks: Record<string, boolean>) => post('/api/tweaks/apply-multiple', { tweaks }),
  tweaksExport: (tweaks: Record<string, boolean>) => post('/api/tweaks/export', { tweaks }),
  tweaksImport: (tweaks: Record<string, boolean>) => post('/api/tweaks/import', { tweaks }),

  // ---- Driver Updater ----
  driverCheckUpdates: () => get<{ total: number; outdated: number; up_to_date: number; drivers: { name: string; version: string; latest_version: string; update_available: boolean; category: string; manufacturer: string; download_url?: string }[] }>('/api/drivers/check-updates'),
  driverDownload: (name: string) => post('/api/drivers/download', { name }),
  driverInstall: (name: string) => post('/api/drivers/install', { name }),
  driverDownloadAll: () => post('/api/drivers/download-all'),
  driverInstallAll: () => post('/api/drivers/install-all'),

  // ---- Software Updater ----
  softwareCheckUpdates: () => get<{ total: number; updates_available: number; up_to_date: number; software: { name: string; current_version: string; latest_version: string; update_available: boolean; download_url: string; category: string }[] }>('/api/software/check-updates'),

  // ---- Duplicate & Large Files ----
  fileDuplicates: () => post<{ duplicates: { original: string; duplicate: string; size: number; original_name: string; duplicate_name: string }[] }>('/api/files/duplicates'),
  fileLarge: (minSizeMb = 500) => post<{ large_files: { path: string; name: string; size: number; category: string }[] }>('/api/files/large', { min_size_mb: minSizeMb }),
  fileDelete: (path: string) => post('/api/files/delete', { path }),

  // ---- File Shredder ----
  fileShred: (path: string, passes = 3) => post('/api/files/shred', { path, passes }),
  fileShredFolder: (path: string, passes = 3) => post('/api/files/shred-folder', { path, passes }),

  // ---- Disk Tools (Defrag/TRIM) ----
  diskDefrag: (drive = 'C:') => post('/api/disk/defrag', { drive }),
  diskTrim: (drive = 'C:') => post('/api/disk/trim', { drive }),
  diskDriveInfo: (drive = 'C:') => post<{ drive: string; total?: number; used?: number; free?: number; percent?: number; model?: string; is_ssd?: boolean }>('/api/disk/drive-info', { drive }),

  // ---- System Repair ----
  repairSfc: () => post('/api/repair/sfc'),
  repairDism: () => post('/api/repair/dism'),
  repairCheckDisk: (drive = 'C:') => post('/api/repair/check-disk', { drive }),

  // ---- Startup Timer ----
  startupTimer: () => get<{ uptime_seconds: number; uptime_formatted: string; boot_time: string; startup_processes: { name: string; pid: number; start_time: string; cpu: number }[]; total_startup_processes: number }>('/api/startup/timer'),

  // ---- Context Menu ----
  contextMenu: () => get<{ items: { key: string; name: string; command: string; location: string }[] }>('/api/context-menu'),
  contextMenuDisable: (key: string) => post('/api/context-menu/disable', { key }),
  contextMenuEnable: (key: string) => post('/api/context-menu/enable', { key }),

  // ---- Speed Test ----
  speedTestPing: (host = '8.8.8.8', count = 4) => post<import('../types').PingResult>('/api/speed-test/ping', { host, count }),
  speedTestDownload: (sizeMb = 25) => post('/api/speed-test/download', { size_mb: sizeMb }),
  speedTestUpload: (sizeMb = 5) => post('/api/speed-test/upload', { size_mb: sizeMb }),
  speedTestAll: () => post<{ ping: { avg_ms: number; min_ms: number; max_ms: number; packet_loss: number }; download: { download_mbps: number }; upload: { upload_mbps: number } }>('/api/speed-test/all'),

  // ---- Hardware Detection ----
  hardwareDetect: () => get<import('../types').HardwareInfo>('/api/hardware/detect'),
  isAdmin: () => get<{ is_admin: boolean }>('/api/hardware/is-admin'),

  // ---- Optimization Compatibility ----
  optimizationsList: () => get<{ safe: import('../types').OptimizationEntry[]; advanced: import('../types').OptimizationEntry[]; experimental: import('../types').OptimizationEntry[] }>('/api/optimizations/list'),
  optimizationCheck: (oid: string) => get<import('../types').CompatibilityCheck>('/api/optimizations/check/' + oid),
  optimizationsCheckMultiple: (ids: string[]) => post<Record<string, import('../types').CompatibilityCheck>>('/api/optimizations/check-multiple', { ids }),

  // ---- AI Endpoints ----
  aiHealthScore: () => get<import('../types').AiHealthScoreResponse>('/api/ai/health-score'),
  aiRecommendations: () => get<import('../types').AiRecommendationsResponse>('/api/ai/recommendations'),
  aiBottlenecks: () => get<import('../types').AiBottlenecksResponse>('/api/ai/bottlenecks'),
  aiMaintenance: () => get<{ predictions: unknown[] }>('/api/ai/maintenance'),
  aiGaming: () => get<{ profiles: unknown[] }>('/api/ai/gaming'),

  // ---- Reset to Windows Defaults ----
  resetToDefaults: () => post<{ success: boolean; message: string; results: { key?: string; value?: string; bcd?: string; action?: string; success: boolean; error?: string }[]; total: number; snapshot: string }>('/api/reset-to-defaults'),

  // ---- Rollback ----
  rollbackSnapshots: () => get<{ snapshots: { file: string; created: string; os: string }[] }>('/api/rollback/snapshots'),
  rollbackRestore: (file: string) => post<{ success: boolean; results: { success: boolean; message: string }[]; total: number; ok: number }>('/api/rollback/restore', { file }),
  rollbackCreateSnapshot: () => post<{ success: boolean; file: string }>('/api/rollback/create-snapshot'),

  // ---- Power Center ----
  powerPlans: () => get<{ plans: { guid: string; name: string; is_active: boolean; description: string }[] }>('/api/power/plans'),
  powerBattery: () => get<{ is_laptop: boolean; charge_percent?: number; status?: string; estimated_remaining?: string }>('/api/power/battery'),
  powerSettings: () => get<{ sleep_timeout: number; hibernate_enabled: boolean; usb_suspend: boolean; pcie_link_state: string; processor_min: number; processor_max: number }>('/api/power/settings'),
  powerSetSleep: (minutes: number) => post('/api/power/sleep', { minutes }),
  powerToggleHibernate: (enable: boolean) => post('/api/power/hibernate', { enable }),
  powerToggleUsbSuspend: (disable: boolean) => post('/api/power/usb-suspend', { disable }),
  powerSetPcieLink: (state: string) => post('/api/power/pcie-link', { state }),
  powerSetProcessor: (min: number, max: number) => post('/api/power/processor', { min, max }),
  powerCreateHighPerf: () => post<{ success: boolean; guid: string }>('/api/power/create-high-perf'),
  powerApplyPlan: (guid: string) => post('/api/power/apply', { guid }),

  // ---- Driver Center ----
  driverHealth: () => get<{ total: number; outdated: number; problems: number; vulnerable: number }>('/api/drivers-center/health'),
  driverBackup: () => post<{ success: boolean; path: string }>('/api/drivers-center/backup'),
  driverRestore: () => post<{ success: boolean }>('/api/drivers-center/restore'),
  driverProblemDevices: () => get<{ devices: { name: string; code: number; problem: string }[] }>('/api/drivers-center/problems'),
  driverVulnerableScan: () => get<{ vulnerable: { name: string; driver: string; risk: string }[] }>('/api/drivers-center/vulnerable'),

  // ---- Plugin System ----
  pluginList: () => get<{ plugins: { id: string; name: string; version: string; author: string; description: string; category: string; status: string; enabled: boolean }[] }>('/api/plugins/list'),
  pluginLoad: (id: string) => post('/api/plugins/load', { id }),
  pluginUnload: (id: string) => post('/api/plugins/unload', { id }),
  pluginEnable: (id: string) => post('/api/plugins/enable', { id }),
  pluginDisable: (id: string) => post('/api/plugins/disable', { id }),
  pluginCreateTemplate: (name: string) => post<{ success: boolean; path: string }>('/api/plugins/create-template', { name }),
  pluginValidate: (path: string) => post<{ success: boolean; errors: string[] }>('/api/plugins/validate', { path }),
  pluginCheckUpdates: () => post<{ updates: number }>('/api/plugins/check-updates'),

  // ---- Automation ----
  automationTasks: () => get<{ tasks: { id: string; name: string; action: string; interval: string; enabled: boolean; last_run: string | null; next_run: string | null }[] }>('/api/automation/tasks'),
  automationToggleTask: (id: string, enable: boolean) => post('/api/automation/toggle', { id, enable }),
  automationRunTask: (id: string) => post('/api/automation/run', { id }),
  automationCreateTask: (name: string, action: string, interval: string) => post('/api/automation/create', { name, action, interval }),
  automationDeleteTask: (id: string) => post('/api/automation/delete', { id }),
  automationTaskHistory: (id: string) => get<{ history: { timestamp: string; status: string; duration: string }[] }>('/api/automation/history/' + id),
  automationSchedulerStart: () => post('/api/automation/scheduler/start'),
  automationSchedulerStop: () => post('/api/automation/scheduler/stop'),
  automationSchedulerStatus: () => get<{ running: boolean }>('/api/automation/scheduler/status'),
  automationPresets: () => get<{ presets: { id: string; name: string; description: string; tasks: string[] }[] }>('/api/automation/presets'),
  automationApplyPreset: (id: string) => post('/api/automation/apply-preset', { id }),

  // ---- Developer Center ----
  devToolsList: () => get<{ tools: { name: string; version: string | null; installed: boolean; category: string }[] }>('/api/devcenter/installed'),
  devSearchPackages: (query: string, source: string) => post<{ packages: { name: string; version: string; source: string }[] }>('/api/devcenter/search', { query, source }),
  devInstallPackage: (name: string, source: string) => post('/api/devcenter/install', { name, source }),
  devCacheClean: () => post<{ success: boolean; freed_bytes: number }>('/api/devcenter/clean-caches'),
  devEnvRepair: () => post<{ success: boolean; results: { action: string; status: string }[] }>('/api/devcenter/repair-path'),

  // ---- Overview (aggregated home screen payload) ----
  overview: () => get<import('../types').Overview>('/api/overview', 60000),
  overviewRefresh: () => post<{ success: boolean }>('/api/overview/refresh'),

  // ---- Presets ----
  presets: () => get<{ presets: import('../types').PresetMode[] }>('/api/presets'),
  optimizeQuick: (preset: string) => post<import('../types').OptimizeRun>('/api/optimize/quick', { preset }, LONG_TIMEOUT),

  // ---- Game profiles ----
  gameProfiles: () => get<{ profiles: import('../types').GameProfileSummary[] }>('/api/game-profiles'),
  installedGames: () => get<import('../types').InstalledGamesSet>('/api/game-profiles/installed'),
  gameProfile: (id: string) => get<{ profile: import('../types').GameProfile }>(`/api/game-profiles/${id}`),
  detectGame: () => get<{ detected: boolean; game_id?: string; game_name?: string; appid?: number }>('/api/game-profiles/detect'),
  applyGameProfile: (profileId: string) => post<{ results: { success: boolean; message: string }[] }>('/api/game-profiles/apply', { profile_id: profileId }, LONG_TIMEOUT),
  revertGameProfile: () => post<{ results: { success: boolean; message: string }[] }>('/api/game-profiles/revert'),
  saveGameProfile: (profileId: string, profile: Record<string, unknown>) => post<{ success: boolean }>('/api/game-profiles/save', { profile_id: profileId, profile }),
  deleteGameProfile: (profileId: string) => del<{ success: boolean }>(`/api/game-profiles/${profileId}`),

  // ---- Optimizer registry ----
  optimizerList: () => get<{ optimizers: string[]; all_categories: string[] }>('/api/optimize/list'),

  // ---- Game library (real installed-game discovery) ----
  gameLibrary: () => get<import('../types').GameLibrary>('/api/game-library'),
  gameLibraryScan: () => post<{ started: boolean; reason?: string }>('/api/game-library/scan'),
  gameLibraryProgress: () => get<import('../types').GameScanProgress>('/api/game-library/progress'),
  gameLibraryCancel: () => post<{ cancelled: boolean }>('/api/game-library/cancel'),
  gameLibraryRoots: () => get<{ roots: string[] }>('/api/game-library/roots'),
  gameLibraryAddRoot: (root: string) => post<{ roots: string[] }>('/api/game-library/roots', { root }),
  gameLibraryRemoveRoot: (root: string) => del<{ roots: string[] }>('/api/game-library/roots', { root }),
  gameLibraryOpen: (id: string) => post<{ opened: boolean }>('/api/game-library/open', { id }),
  gameLibraryLaunch: (id: string) => post<{ launched: boolean }>('/api/game-library/launch', { id }),
  gameLibraryRunning: () => get<{ running: string[] }>('/api/game-library/running'),
  gameLibraryFavorites: () => get<{ favorites: string[] }>('/api/game-library/favorites'),
  gameLibraryFavoriteAdd: (id: string) => post<{ favorites: string[] }>('/api/game-library/favorites', { id }),
  gameLibraryFavoriteRemove: (id: string) => del<{ favorites: string[] }>('/api/game-library/favorites', { id }),
  gameLibrarySession: (id: string) => get<import('../types').GameSessionData>(`/api/game-library/session/${encodeURIComponent(id)}`),
  /* Manual imports (Gaming Center V2) */
  gameLibraryManual: () => get<import('../types').ManualLibrary>('/api/game-library/manual'),
  gameLibraryResolveShortcut: (lnk: string) => post<{ target: string | null; args: string; exists: boolean; warning?: string }>('/api/game-library/resolve-shortcut', { lnk }),
  gameLibraryScanFolder: (folder: string) => post<{ folder: string; candidates: import('../types').GameExeCandidate[] }>('/api/game-library/scan-folder', { folder }),
  gameLibraryAddExe: (payload: { exe_path: string; name?: string; args?: string; emulator_id?: string | null }) => post<{ game: import('../types').ManualGameEntry; updated: boolean }>('/api/game-library/manual/exe', payload),
  gameLibraryAddFolder: (payload: { folder: string; exe_path?: string; name?: string }) => post<{ game: import('../types').ManualGameEntry; updated: boolean }>('/api/game-library/manual/folder', payload),
  gameLibraryUpdateManual: (id: string, fields: { name?: string; args?: string; exe_path?: string; emulator_id?: string | null }) => patch<{ game: import('../types').ManualGameEntry }>(`/api/game-library/manual/${encodeURIComponent(id)}`, fields),
  gameLibraryRemoveManual: (id: string) => del<{ removed: string }>(`/api/game-library/manual/${encodeURIComponent(id)}`),
  gameLibraryEmulators: () => get<{ emulators: import('../types').EmulatorEntry[] }>('/api/game-library/emulators'),
  gameLibraryAddEmulator: (payload: { name: string; exe_path: string; args?: string }) => post<{ emulator: import('../types').EmulatorEntry }>('/api/game-library/emulators', payload),
  gameLibraryRemoveEmulator: (id: string) => del<{ removed: string }>(`/api/game-library/emulators/${encodeURIComponent(id)}`),
  gameLibraryManualLaunch: (id: string) => post<{ created: boolean; pid?: number; error?: string }>('/api/game-library/manual-launch', { id }),
}
