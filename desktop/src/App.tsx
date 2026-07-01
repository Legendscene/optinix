import { useState, lazy, Suspense } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Sidebar } from './components/layout/Sidebar'
import { TopBar } from './components/layout/TopBar'
import { useSystemInfo } from './hooks/useSystemInfo'
import { Dashboard } from './components/pages/Dashboard'
import { Skeleton } from './components/ui/Skeleton'

const CpuPage = lazy(() => import('./components/pages/CpuPage').then(m => ({ default: m.CpuPage })))
const GpuPage = lazy(() => import('./components/pages/GpuPage').then(m => ({ default: m.GpuPage })))
const MemoryPage = lazy(() => import('./components/pages/MemoryPage').then(m => ({ default: m.MemoryPage })))
const DiskPage = lazy(() => import('./components/pages/DiskPage').then(m => ({ default: m.DiskPage })))
const NetworkPage = lazy(() => import('./components/pages/NetworkPage').then(m => ({ default: m.NetworkPage })))
const GamingPage = lazy(() => import('./components/pages/GamingPage').then(m => ({ default: m.GamingPage })))
const CleanupPage = lazy(() => import('./components/pages/CleanupPage').then(m => ({ default: m.CleanupPage })))
const ExtremePage = lazy(() => import('./components/pages/ExtremePage').then(m => ({ default: m.ExtremePage })))
const ServicesPage = lazy(() => import('./components/pages/ServicesPage').then(m => ({ default: m.ServicesPage })))
const StartupPage = lazy(() => import('./components/pages/StartupPage').then(m => ({ default: m.StartupPage })))
const SecurityPage = lazy(() => import('./components/pages/SecurityPage').then(m => ({ default: m.SecurityPage })))
const OverclockPage = lazy(() => import('./components/pages/OverclockPage').then(m => ({ default: m.OverclockPage })))
const DeveloperPage = lazy(() => import('./components/pages/DeveloperPage').then(m => ({ default: m.DeveloperPage })))
const ToolboxPage = lazy(() => import('./components/pages/ToolboxPage').then(m => ({ default: m.ToolboxPage })))
const DriversPage = lazy(() => import('./components/pages/DriversPage').then(m => ({ default: m.DriversPage })))
const SettingsPage = lazy(() => import('./components/pages/SettingsPage').then(m => ({ default: m.SettingsPage })))
const AiOptimizerPage = lazy(() => import('./components/pages/AiOptimizerPage').then(m => ({ default: m.AiOptimizerPage })))
const InternetBoosterPage = lazy(() => import('./components/pages/InternetBoosterPage').then(m => ({ default: m.default })))
const PrivacyPage = lazy(() => import('./components/pages/PrivacyPage').then(m => ({ default: m.default })))
const RegistryPage = lazy(() => import('./components/pages/RegistryPage').then(m => ({ default: m.default })))
const WindowsTweaksPage = lazy(() => import('./components/pages/WindowsTweaksPage').then(m => ({ default: m.default })))
const PluginsPage = lazy(() => import('./components/pages/PluginsPage').then(m => ({ default: m.default })))
const ExtensionsPage = lazy(() => import('./components/pages/ExtensionsPage').then(m => ({ default: m.default })))
const OneClickPage = lazy(() => import('./components/pages/OneClickPage').then(m => ({ default: m.OneClickPage })))
const PowerPlansPage = lazy(() => import('./components/pages/PowerPlansPage').then(m => ({ default: m.PowerPlansPage })))
const SchedulerPage = lazy(() => import('./components/pages/SchedulerPage').then(m => ({ default: m.SchedulerPage })))
const GameModePage = lazy(() => import('./components/pages/GameModePage').then(m => ({ default: m.GameModePage })))
const DebloatPage = lazy(() => import('./components/pages/DebloatPage').then(m => ({ default: m.DebloatPage })))
const BiosPage = lazy(() => import('./components/pages/BiosPage').then(m => ({ default: m.BiosPage })))
const PeripheralPage = lazy(() => import('./components/pages/PeripheralPage').then(m => ({ default: m.PeripheralPage })))
const DevicePage = lazy(() => import('./components/pages/DevicePage').then(m => ({ default: m.DevicePage })))
const DriverBoosterPage = lazy(() => import('./components/pages/DriverBoosterPage').then(m => ({ default: m.DriverBoosterPage })))
const SoftwarePage = lazy(() => import('./components/pages/SoftwarePage').then(m => ({ default: m.SoftwarePage })))
const FileToolsPage = lazy(() => import('./components/pages/FileToolsPage').then(m => ({ default: m.FileToolsPage })))
const SystemRepairPage = lazy(() => import('./components/pages/SystemRepairPage').then(m => ({ default: m.SystemRepairPage })))
const SpeedTestPage = lazy(() => import('./components/pages/SpeedTestPage').then(m => ({ default: m.SpeedTestPage })))

const PageFallback = () => (
  <div className="p-6 space-y-6">
    <div className="space-y-3">
      <Skeleton variant="text" width="250px" height="28px" />
      <Skeleton variant="text" width="350px" height="16px" />
    </div>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="100px" />)}
    </div>
    <Skeleton variant="rectangular" height="300px" />
    <div className="grid grid-cols-3 gap-4">
      {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="160px" />)}
    </div>
  </div>
)

const pages: Record<string, React.ComponentType<{ systemInfo: ReturnType<typeof useSystemInfo>['data'] }>> = {
  dashboard: Dashboard,
  cpu: CpuPage,
  gpu: GpuPage,
  memory: MemoryPage,
  storage: DiskPage,
  network: NetworkPage,
  gaming: GamingPage,
  cleanup: CleanupPage,
  extreme: ExtremePage,
  services: ServicesPage,
  startup: StartupPage,
  security: SecurityPage,
  overclock: OverclockPage,
  developer: DeveloperPage,
  toolbox: ToolboxPage,
  drivers: DriversPage,
  settings: SettingsPage,
  'ai-optimizer': AiOptimizerPage,
  internet: InternetBoosterPage,
  privacy: PrivacyPage,
  registry: RegistryPage,
  windows: WindowsTweaksPage,
  plugins: PluginsPage,
  extensions: ExtensionsPage,
  oneclick: OneClickPage,
  power: PowerPlansPage,
  scheduler: SchedulerPage,
  'game-mode': GameModePage,
  debloat: DebloatPage,
  bios: BiosPage,
  peripheral: PeripheralPage,
  device: DevicePage,
  'drivers-update': DriverBoosterPage,
  software: SoftwarePage,
  'file-tools': FileToolsPage,
  'system-repair': SystemRepairPage,
  'speed-test': SpeedTestPage,
}

export default function App() {
  const [active, setActive] = useState('dashboard')
  const { data: sysInfo } = useSystemInfo()

  const Page = pages[active] || Dashboard

  return (
    <div className="flex h-full w-full bg-surface-0">
      <Sidebar active={active} onNavigate={setActive} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar
          cpu={sysInfo?.cpu.percent}
          ram={sysInfo?.memory.percent}
          disk={sysInfo?.disk[0]?.percent}
          network={sysInfo ? `${Math.round((sysInfo.network?.speed_down || 0) / 1024)} KB/s` : '--'}
          temp={sysInfo?.cpu?.temperature ? `${Math.round(sysInfo.cpu.temperature)}°` : undefined}
        />
        <main className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={active}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <Suspense fallback={<PageFallback />}>
                <Page systemInfo={sysInfo} />
              </Suspense>
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}