import { Search, Bell } from 'lucide-react'
import { StatusPill } from '../ui/StatusPill'

interface TopBarProps {
  cpu?: number
  ram?: number
  disk?: number
  network?: string
  temp?: string
}

export function TopBar({ cpu = 0, ram = 0, disk = 0, network = '--', temp = '--' }: TopBarProps) {
  return (
    <header className="flex items-center justify-between h-14 px-5 border-b border-border bg-surface-0/80 backdrop-blur-xl shrink-0">
      <div className="flex items-center gap-3 flex-1 max-w-md">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-2 border border-border text-text-tertiary text-sm w-full max-w-xs">
          <Search size={14} />
          <span className="flex-1">Search...</span>
          <kbd className="px-1 py-0.5 rounded bg-surface-3 text-[10px] font-mono text-text-tertiary">Ctrl+K</kbd>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <StatusPill label="CPU" value={`${cpu}%`} color={cpu > 80 ? '#ef4444' : '#22c55e'} alert={cpu > 90} />
        <StatusPill label="RAM" value={`${ram}%`} color={ram > 80 ? '#ef4444' : '#22c55e'} alert={ram > 90} />
        <StatusPill label="DISK" value={`${disk}%`} color={disk > 85 ? '#ef4444' : '#22c55e'} alert={disk > 95} />
        <StatusPill label="NET" value={network} />
        {temp !== '--' && <StatusPill label="TEMP" value={temp} />}
        <div className="w-px h-5 bg-border mx-1" />
        <button className="p-2 rounded-lg hover:bg-surface-2 text-text-tertiary hover:text-text transition-colors">
          <Bell size={16} />
        </button>
        <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-white text-xs font-semibold">O</div>
      </div>
    </header>
  )
}
