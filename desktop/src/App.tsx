import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { lazy, Suspense } from 'react'
import { motion, MotionConfig } from 'framer-motion'
import { Sidebar } from './components/layout/Sidebar'
import { PageAtmosphere } from './components/layout/PageAtmosphere'
import { TopBar } from './components/layout/TopBar'
import { CommandPalette, type PaletteAction } from './components/CommandPalette'
import { HomePage } from './components/pages/HomePage'
import { PersonalizationPage } from './components/pages/PersonalizationPage'
import { GamesPage } from './components/pages/GamesPage'
import { ZonePage } from './components/pages/ZonePage'
import { OptimizerConsolePage } from './components/pages/OptimizerConsolePage'
import { useLibrary } from './hooks/useLibrary'
import { useSystemStore } from './store/systemStore'
import { useAdminCheck } from './hooks/useAdminCheck'
import { useNavigation } from './hooks/useNavigation'
import { useMotionPreference } from './hooks/useMotionPreference'
import { ZONES, TOOL_MAP, type ZoneId } from './nav'
import { api } from './lib/api'
import type { SystemInfo } from './types'

/* Every legacy page stays reachable. The overview and the seven zone hubs are
   eager; the rest load on demand so the initial bundle stays small. */
interface LegacyPageProps {
  systemInfo: SystemInfo | null
  onNavigate: (id: string) => void
}

type PageComponent = React.ComponentType<LegacyPageProps>

/**
 * The 53 existing pages were written independently and each declares its own
 * prop shape - some require `systemInfo`, some require `onNavigate`, some take
 * neither. Rather than rewrite 53 signatures, one adapter erases the type and
 * the shell passes both props to every page. The cast is confined to here.
 */
function page(loader: () => Promise<{ default: React.ComponentType<any> }>): PageComponent {
  return lazy(loader) as unknown as PageComponent
}

const CpuPage = page(() => import('./components/pages/CpuPage').then(m => ({ default: m.CpuPage })))
const GpuPage = page(() => import('./components/pages/GpuPage').then(m => ({ default: m.GpuPage })))
const MemoryPage = page(() => import('./components/pages/MemoryPage').then(m => ({ default: m.MemoryPage })))
const DiskPage = page(() => import('./components/pages/DiskPage').then(m => ({ default: m.DiskPage })))
const NetworkPage = page(() => import('./components/pages/NetworkPage').then(m => ({ default: m.NetworkPage })))
const NetworkIntelligencePage = page(() => import('./components/pages/NetworkIntelligencePage').then(m => ({ default: m.NetworkIntelligencePage })))
const GamingPage = page(() => import('./components/pages/GamingPage').then(m => ({ default: m.GamingPage })))
const CleanupPage = page(() => import('./components/pages/CleanupPage').then(m => ({ default: m.CleanupPage })))
const ExtremePage = page(() => import('./components/pages/ExtremePage').then(m => ({ default: m.ExtremePage })))
const ServicesPage = page(() => import('./components/pages/ServicesPage').then(m => ({ default: m.ServicesPage })))
const StartupPage = page(() => import('./components/pages/StartupPage').then(m => ({ default: m.StartupPage })))
const SecurityPage = page(() => import('./components/pages/SecurityPage').then(m => ({ default: m.SecurityPage })))
const OverclockPage = page(() => import('./components/pages/OverclockPage').then(m => ({ default: m.OverclockPage })))
const DeveloperPage = page(() => import('./components/pages/DeveloperPage').then(m => ({ default: m.DeveloperPage })))
const ToolboxPage = page(() => import('./components/pages/ToolboxPage').then(m => ({ default: m.ToolboxPage })))
const DriversPage = page(() => import('./components/pages/DriversPage').then(m => ({ default: m.DriversPage })))
const SettingsPage = page(() => import('./components/pages/SettingsPage').then(m => ({ default: m.SettingsPage })))
const AiOptimizerPage = page(() => import('./components/pages/AiOptimizerPage').then(m => ({ default: m.AiOptimizerPage })))
const InternetBoosterPage = page(() => import('./components/pages/InternetBoosterPage').then(m => ({ default: m.default })))
const PrivacyPage = page(() => import('./components/pages/PrivacyPage').then(m => ({ default: m.default })))
const RegistryPage = page(() => import('./components/pages/RegistryPage').then(m => ({ default: m.default })))
const WindowsTweaksPage = page(() => import('./components/pages/WindowsTweaksPage').then(m => ({ default: m.default })))
const PluginsPage = page(() => import('./components/pages/PluginsPage').then(m => ({ default: m.default })))
const ExtensionsPage = page(() => import('./components/pages/ExtensionsPage').then(m => ({ default: m.default })))
const OneClickPage = page(() => import('./components/pages/OneClickPage').then(m => ({ default: m.OneClickPage })))
const PowerPlansPage = page(() => import('./components/pages/PowerPlansPage').then(m => ({ default: m.PowerPlansPage })))
const SchedulerPage = page(() => import('./components/pages/SchedulerPage').then(m => ({ default: m.SchedulerPage })))
const GameModePage = page(() => import('./components/pages/GameModePage').then(m => ({ default: m.GameModePage })))
const DebloatPage = page(() => import('./components/pages/DebloatPage').then(m => ({ default: m.DebloatPage })))
const BiosPage = page(() => import('./components/pages/BiosPage').then(m => ({ default: m.BiosPage })))
const PeripheralPage = page(() => import('./components/pages/PeripheralPage').then(m => ({ default: m.PeripheralPage })))
const DevicePage = page(() => import('./components/pages/DevicePage').then(m => ({ default: m.DevicePage })))
const DriverBoosterPage = page(() => import('./components/pages/DriverBoosterPage').then(m => ({ default: m.DriverBoosterPage })))
const SoftwarePage = page(() => import('./components/pages/SoftwarePage').then(m => ({ default: m.SoftwarePage })))
const FileToolsPage = page(() => import('./components/pages/FileToolsPage').then(m => ({ default: m.FileToolsPage })))
const SystemRepairPage = page(() => import('./components/pages/SystemRepairPage').then(m => ({ default: m.SystemRepairPage })))
const SpeedTestPage = page(() => import('./components/pages/SpeedTestPage').then(m => ({ default: m.SpeedTestPage })))
const RollbackPage = page(() => import('./components/pages/RollbackPage'))
const PowerCenterPage = page(() => import('./components/pages/PowerCenterPage').then(m => ({ default: m.default })))
const DriverCenterPage = page(() => import('./components/pages/DriverCenterPage').then(m => ({ default: m.default })))
const AutomationPage = page(() => import('./components/pages/AutomationPage').then(m => ({ default: m.default })))
const HealthScoresPage = page(() => import('./components/pages/HealthScoresPage').then(m => ({ default: m.HealthScoresPage })))
const LiveMonitorPage = page(() => import('./components/pages/LiveMonitorPage').then(m => ({ default: m.LiveMonitorPage })))
const DiagnosticsPage = page(() => import('./components/pages/DiagnosticsPage').then(m => ({ default: m.DiagnosticsPage })))
const ReportsPage = page(() => import('./components/pages/ReportsPage').then(m => ({ default: m.ReportsPage })))
const NotificationsPage = page(() => import('./components/pages/NotificationsPage').then(m => ({ default: m.NotificationsPage })))
const TimelinePage = page(() => import('./components/pages/TimelinePage').then(m => ({ default: m.TimelinePage })))
const StorageMapPage = page(() => import('./components/pages/StorageMapPage').then(m => ({ default: m.StorageMapPage })))
const DeviceInfoPage = page(() => import('./components/pages/DeviceInfoPage').then(m => ({ default: m.DeviceInfoPage })))
const ToolsCenterPage = page(() => import('./components/pages/ToolsCenterPage').then(m => ({ default: m.ToolsCenterPage })))
const MarketplacePage = page(() => import('./components/pages/MarketplacePage').then(m => ({ default: m.MarketplacePage })))
const AISettingsPage = page(() => import('./components/pages/AISettingsPage').then(m => ({ default: m.AISettingsPage })))
const DashboardPage = page(() => import('./components/pages/Dashboard').then(m => ({ default: m.Dashboard })))

/* Route ids renamed from the old shell (id collisions that made these pages
   unreachable): network -> network-tuning, gaming -> game-tweaks,
   diagnostics -> troubleshooter, settings -> general. */
const PAGES: Record<string, PageComponent> = {
  dashboard: DashboardPage,
  cpu: CpuPage, gpu: GpuPage, memory: MemoryPage, storage: DiskPage,
  'network-tuning': NetworkPage, 'network-intelligence': NetworkIntelligencePage,
  'game-tweaks': GamingPage, cleanup: CleanupPage,
  extreme: ExtremePage, services: ServicesPage, startup: StartupPage,
  security: SecurityPage, overclock: OverclockPage, developer: DeveloperPage,
  toolbox: ToolboxPage, drivers: DriversPage, general: SettingsPage,
  theme: SettingsPage, 'ai-optimizer': AiOptimizerPage, internet: InternetBoosterPage,
  privacy: PrivacyPage, registry: RegistryPage, windows: WindowsTweaksPage,
  plugins: PluginsPage, extensions: ExtensionsPage, oneclick: OneClickPage,
  power: PowerPlansPage, scheduler: SchedulerPage, 'game-mode': GameModePage,
  debloat: DebloatPage, bios: BiosPage, peripheral: PeripheralPage,
  device: DevicePage, 'drivers-update': DriverBoosterPage, software: SoftwarePage,
  'file-tools': FileToolsPage, 'system-repair': SystemRepairPage,
  'speed-test': SpeedTestPage, rollback: RollbackPage, 'power-center': PowerCenterPage,
  'driver-center': DriverCenterPage, automation: AutomationPage,
  'health-scores': HealthScoresPage, 'live-monitor': LiveMonitorPage,
  'troubleshooter': DiagnosticsPage, reports: ReportsPage,
  notifications: NotificationsPage, timeline: TimelinePage,
  'storage-map': StorageMapPage, 'device-info': DeviceInfoPage,
  'tools-center': ToolsCenterPage, marketplace: MarketplacePage,
  'ai-settings': AISettingsPage,
}

const ZONE_IDS = new Set<string>(ZONES.map((z) => z.id))

function PageFallback() {
  return (
    <div className="max-w-[1120px] space-y-4">
      <div className="h-9 w-56 rounded-lg bg-surface-2 animate-pulse-subtle" />
      <div className="surface-card h-[180px] animate-pulse-subtle" />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="surface-card h-[84px] animate-pulse-subtle" />
        ))}
      </div>
      <div className="surface-card h-[220px] animate-pulse-subtle" />
    </div>
  )
}

export default function App() {
  const nav = useNavigation()
  const library = useLibrary()
  const vitals = useSystemStore()
  const { isAdmin } = useAdminCheck()
  const reducedMotion = useMotionPreference()

  const [paletteOpen, setPaletteOpen] = useState(false)
  const [optimizing, setOptimizing] = useState(false)
  const [unread, setUnread] = useState(0)
  const mainRef = useRef<HTMLElement>(null)

  const route = nav.route
  const zone: ZoneId = ZONE_IDS.has(route)
    ? (route as ZoneId)
    : (TOOL_MAP[route]?.zone ?? 'home')

  const go = useCallback((id: string) => {
    nav.navigate(id)
    library.touch(id)
    mainRef.current?.scrollTo({ top: 0 })
  }, [nav, library])

  /* Ctrl+K / Cmd+K opens the palette. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  /* Unread notification count, polled slowly and only while the app is visible. */
  useEffect(() => {
    let id: ReturnType<typeof setInterval> | undefined
    const poll = () => {
      if (document.hidden) return
      api.notificationsUnread().then((r) => setUnread(r.count ?? 0)).catch(() => {})
    }
    poll()
    id = setInterval(poll, 60_000)
    const onVis = () => { if (!document.hidden) poll() }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      if (id) clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])

  const actions = useMemo<PaletteAction[]>(() => [
    {
      id: 'action:boost',
      label: 'Run a quick optimization',
      description: 'Cleanup, network tuning and memory trim',
      keywords: ['boost', 'optimize', 'clean', 'speed', 'fix', 'tune'],
      run: () => go('oneclick'),
    },
    {
      id: 'action:free-ram',
      label: 'Free memory now',
      description: 'Trim working sets of non-essential processes',
      keywords: ['ram', 'memory', 'free', 'trim', 'cache'],
      run: () => go('memory'),
    },
    {
      id: 'action:scan-junk',
      label: 'Scan for junk files',
      description: 'Find reclaimable space on the system drive',
      keywords: ['junk', 'cleanup', 'scan', 'disk', 'space', 'temp'],
      run: () => go('cleanup'),
    },
    {
      id: 'action:measure-ping',
      label: 'Measure ping',
      description: 'Latency test against 1.1.1.1',
      keywords: ['ping', 'latency', 'network', 'test', 'lag'],
      run: () => go('speed-test'),
    },
    {
      id: 'action:health',
      label: 'Run a health check',
      description: 'Score PC, Windows, gaming, storage and security',
      keywords: ['health', 'score', 'check', 'diagnose', 'audit'],
      run: () => go('health-scores'),
    },
    ...(isAdmin
      ? []
      : [{
          id: 'action:admin-help',
          label: 'How to run as Administrator',
          description: 'Most optimizations need elevated rights',
          keywords: ['admin', 'administrator', 'elevated', 'privilege', 'permission', 'uac'],
          run: () => go('general'),
        }]),
  ], [go, isAdmin])

  const isZone = ZONE_IDS.has(route)
  /* Destinations that render a dedicated page instead of a tool hub.
     Same erased-props adapter as PAGES: home/games/personalization take
     library + the optimizing callback; reports/monitor ignore them. */
  const DIRECT: Record<string, React.ComponentType<any>> = {
    home: HomePage,
    games: GamesPage,
    personalization: PersonalizationPage,
    /* reports/monitor have exactly one tool each; the destination IS that
       page, so the sidebar lands there without a pointless hub hop. */
    reports: PAGES['reports'],
    monitor: PAGES['live-monitor'],
  }
  const DirectPage = isZone ? DIRECT[route] : undefined
  const Page = !isZone && route !== 'home' ? PAGES[route] : undefined

  return (
    /* Reduced motion is decided once here and inherited by every motion
       element below, so individual components never have to re-check it. */
    <MotionConfig reducedMotion={reducedMotion ? 'always' : 'never'}>
    {/* w-full: the preferences provider renders a flex wrapper, so without it
        this shell shrink-wraps narrow pages and leaves a dead strip on the
        right instead of filling the window. */}
    <div id="app-root" className="flex h-screen w-full overflow-hidden text-text">
      <Sidebar
        active={route}
        zone={zone}
        onNavigate={go}
        onOpenPalette={() => setPaletteOpen(true)}
        library={library}
        isAdmin={isAdmin}
      />

      <div className="relative flex-1 flex flex-col min-w-0 min-h-0">
        <PageAtmosphere />
        <TopBar
          route={route}
          zone={zone}
          vitals={{
            cpu: vitals.cpu,
            ram: vitals.ram,
            disk: vitals.disk,
            temp: vitals.temp,
          }}
          onOpenPalette={() => setPaletteOpen(true)}
          onNavigate={go}
          unreadNotifications={unread}
          optimizing={optimizing}
        />

        {/* z-10 keeps the scrolling content above the PageAtmosphere layer;
            the layer stays visible through the transparent main background. */}
        <main ref={mainRef} className="relative z-10 flex-1 overflow-y-auto overflow-x-hidden px-6 py-5">
          {/* Depth-aware page transition: keying on the route remounts the
              subtree so every page enters with one restrained rise.
              The 0.5% scale is what gives the change a sense of depth
              (content arrives from slightly behind the chrome) without the
              cost of a blur filter on a full page.
              When the user asked for reduced motion it renders statically
              (initial=false skips the enter animation entirely). */}
          <motion.div
            key={route}
            initial={reducedMotion ? false : { opacity: 0, y: 10, scale: 0.995 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.26, ease: [0.25, 1, 0.5, 1] }}
            style={{ transformOrigin: '50% 0%' }}
          >
            {DirectPage ? (
              <DirectPage
                systemInfo={vitals.snapshot}
                onNavigate={go}
                library={library}
                onOptimizingChange={setOptimizing}
              />
            ) : isZone ? (
              route === 'optimizer' ? (
                <OptimizerConsolePage onNavigate={go} library={library} />
              ) : (
                <ZonePage zone={route as ZoneId} onNavigate={go} library={library} />
              )
            ) : (
              <Suspense fallback={<PageFallback />}>
                {Page ? <Page systemInfo={vitals.snapshot} onNavigate={go} /> : <ZonePage zone={zone} onNavigate={go} library={library} />}
              </Suspense>
            )}
          </motion.div>
        </main>
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onNavigate={go}
        library={library}
        actions={actions}
      />
    </div>
    </MotionConfig>
  )
}
