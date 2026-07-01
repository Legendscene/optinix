const BASE = ''

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { signal: AbortSignal.timeout(10000) })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(30000),
  })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

export const api = {
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
  optimize: (cat: string) => post<unknown>(`/api/optimize/${cat}`),
  optimizeAll: () => post<Record<string, unknown>>('/api/optimize/all'),
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
  speedTestPing: (host = '8.8.8.8', count = 4) => post('/api/speed-test/ping', { host, count }),
  speedTestDownload: (sizeMb = 25) => post('/api/speed-test/download', { size_mb: sizeMb }),
  speedTestUpload: (sizeMb = 5) => post('/api/speed-test/upload', { size_mb: sizeMb }),
  speedTestAll: () => post<{ ping: { avg_ms: number; min_ms: number; max_ms: number; packet_loss: number }; download: { download_mbps: number }; upload: { upload_mbps: number } }>('/api/speed-test/all'),
}
