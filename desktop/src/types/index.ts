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
