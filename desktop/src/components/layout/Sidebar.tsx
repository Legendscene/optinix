import { useState } from 'react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'
import {
  LayoutDashboard, Sparkles, Cpu, Monitor, MemoryStick as MemoryIcon,
  HardDrive, Wifi, Gamepad2, Eraser, Zap, Settings2, Shield,
  Power, Battery, Clock, Wrench, Code, Puzzle, Users,
  ChevronLeft, ChevronRight, FolderKanban,
  ScanLine as Scan, FileCode, Globe, Trash2, Play, Mouse,
} from 'lucide-react'

interface NavItem { id: string; label: string; icon: ReactNode; badge?: string }

const sections: { title?: string; items: NavItem[] }[] = [
  { items: [{ id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> }] },
  { title: 'Optimize', items: [
    { id: 'oneclick', label: 'One Click Optimize', icon: <Zap size={16} /> },
    { id: 'ai-optimizer', label: 'AI Optimizer', icon: <Sparkles size={16} /> },
    { id: 'cleanup', label: 'Cleanup', icon: <Eraser size={16} /> },
    { id: 'extreme', label: 'Extreme Mode', icon: <Zap size={16} />, badge: 'Danger' },
  ]},
  { title: 'Hardware', items: [
    { id: 'cpu', label: 'CPU', icon: <Cpu size={16} /> },
    { id: 'gpu', label: 'GPU', icon: <Monitor size={16} /> },
    { id: 'memory', label: 'Memory', icon: <MemoryIcon size={16} /> },
    { id: 'storage', label: 'Storage', icon: <HardDrive size={16} /> },
    { id: 'bios', label: 'BIOS', icon: <Settings2 size={16} /> },
    { id: 'peripheral', label: 'Peripherals', icon: <Mouse size={16} /> },
    { id: 'device', label: 'Devices', icon: <Monitor size={16} /> },
  ]},
  { title: 'Network', items: [
    { id: 'network', label: 'Network', icon: <Wifi size={16} /> },
    { id: 'internet', label: 'Internet Booster', icon: <Globe size={16} /> },
  ]},
  { title: 'System', items: [
    { id: 'gaming', label: 'Gaming', icon: <Gamepad2 size={16} /> },
    { id: 'game-mode', label: 'Game Mode', icon: <Play size={16} /> },
    { id: 'debloat', label: 'Debloater', icon: <Trash2 size={16} /> },
    { id: 'startup', label: 'Startup Manager', icon: <Power size={16} /> },
    { id: 'services', label: 'Services', icon: <Settings2 size={16} /> },
    { id: 'security', label: 'Security', icon: <Shield size={16} /> },
    { id: 'privacy', label: 'Privacy', icon: <Users size={16} /> },
    { id: 'power', label: 'Power Plans', icon: <Battery size={16} /> },
    { id: 'scheduler', label: 'Scheduler', icon: <Clock size={16} /> },
  ]},
  { title: 'Tools', items: [
    { id: 'registry', label: 'Registry', icon: <FileCode size={16} /> },
    { id: 'drivers', label: 'Drivers', icon: <Scan size={16} /> },
    { id: 'windows', label: 'Windows Tweaks', icon: <Wrench size={16} /> },
    { id: 'developer', label: 'Dev Tools', icon: <Code size={16} /> },
    { id: 'toolbox', label: 'Toolbox', icon: <FolderKanban size={16} /> },
    { id: 'plugins', label: 'Plugins', icon: <Puzzle size={16} /> },
  ]},
  { title: 'Other', items: [
    { id: 'settings', label: 'Settings', icon: <Settings2 size={16} /> },
  ]},
]

interface SidebarProps {
  active: string
  onNavigate: (id: string) => void
}

export function Sidebar({ active, onNavigate }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={cn(
      'flex flex-col bg-surface-1 border-r border-border h-full transition-all duration-300 relative',
      collapsed ? 'w-[52px]' : 'w-[220px]'
    )}>
      <div className="flex items-center gap-2 px-4 h-14 border-b border-border shrink-0">
        <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center shrink-0">
          <Zap size={14} className="text-white" />
        </div>
        {!collapsed && <span className="font-semibold text-sm tracking-tight">Optinix</span>}
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4 scrollbar-thin">
        {sections.map((section, i) => (
          <div key={i}>
            {section.title && !collapsed && (
              <div className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-text-tertiary">{section.title}</div>
            )}
            <div className="space-y-0.5">
              {section.items.map(item => (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={cn(
                    'flex items-center gap-2.5 w-full px-2 py-1.5 rounded-lg text-sm transition-all duration-150',
                    'hover:bg-surface-2',
                    active === item.id
                      ? 'bg-accent-dim text-accent font-medium'
                      : 'text-text-secondary hover:text-text'
                  )}
                  title={collapsed ? item.label : undefined}
                >
                  <span className="shrink-0">{item.icon}</span>
                  {!collapsed && (
                    <span className="truncate flex-1 text-left">{item.label}</span>
                  )}
                  {!collapsed && item.badge && (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-dim text-red uppercase">{item.badge}</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t border-border text-text-tertiary hover:text-text hover:bg-surface-2 transition-colors shrink-0"
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
  )
}
