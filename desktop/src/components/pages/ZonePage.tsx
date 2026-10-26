import { Star, ArrowRight, AlertTriangle, ShieldAlert } from 'lucide-react'
import { cn } from '../../lib/utils'
import { PageHero } from '../ui/PageHero'
import {
  ZONE_MAP, toolsInZone, groupsInZone, type ZoneId, type Tool,
} from '../../nav'
import type { Library } from '../../hooks/useLibrary'

interface ZonePageProps {
  zone: ZoneId
  onNavigate: (id: string) => void
  library: Library
}

export function ZonePage({ zone, onNavigate, library }: ZonePageProps) {
  const meta = ZONE_MAP[zone]
  if (!meta) return null

  const tools = toolsInZone(zone)
  const groups = groupsInZone(zone)
  const pinned = tools.filter((t) => library.isFavorite(t.id))
  const rest = tools.filter((t) => !library.isFavorite(t.id))
  const needsAdmin = tools.filter((t) => t.badge === 'admin').length
  const ZoneIcon = meta.icon

  return (
    <div className="page animate-rise stagger-rise">
      {/* Zone header: the same band every tool page opens with, so a hub and
          the page behind it belong to one visual family. The four readings
          are counted from the zone's own tool list, nothing invented. */}
      <PageHero
        className="mb-6"
        eyebrow={meta.tagline}
        title={meta.label}
        subtitle={meta.purpose}
        icon={<ZoneIcon size={19} />}
        stats={[
          { label: 'Tools', value: String(tools.length) },
          { label: 'Groups', value: String(groups.length) },
          { label: 'Pinned', value: String(pinned.length), tone: pinned.length ? 'accent' : 'default' },
          { label: 'Need admin', value: String(needsAdmin), tone: needsAdmin ? 'warn' : 'default' },
        ]}
      />

      {pinned.length > 0 && (
        <section className="mb-8">
          <SectionLabel>Pinned</SectionLabel>
          <div className="flex flex-wrap gap-2.5">
            {pinned.map((tool) => (
              <ToolCard
                key={tool.id}
                tool={tool}
                onOpen={() => onNavigate(tool.id)}
                onTogglePin={() => library.toggleFavorite(tool.id)}
                pinned
              />
            ))}
          </div>
        </section>
      )}

      {groups.map((group) => {
        const items = rest.filter((t) => t.group === group)
        if (!items.length) return null
        return (
          <section key={group} className="mb-8">
            <SectionLabel>{group}</SectionLabel>
            {/* Flex, not a fixed 3-column grid: a group of two tools used to
                leave a third of the row empty. Cards now grow to fill it. */}
            <div className="flex flex-wrap gap-2.5">
              {items.map((tool) => (
                <ToolCard
                  key={tool.id}
                  tool={tool}
                  onOpen={() => onNavigate(tool.id)}
                  onTogglePin={() => library.toggleFavorite(tool.id)}
                />
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h2 className="eyebrow accent-rail mb-3">{children}</h2>
}

interface ToolCardProps {
  tool: Tool
  onOpen: () => void
  onTogglePin: () => void
  pinned?: boolean
}

function ToolCard({ tool, onOpen, onTogglePin, pinned }: ToolCardProps) {
  const Icon = tool.icon
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
      className={cn(
        'surface-card surface-card-interactive card-depth sheen group relative p-3.5 cursor-pointer',
        /* Grow to fill a partial row, but never into a full-width strip:
           one tool alone in its group stays a card, not a banner. */
        'grow basis-[272px] max-w-[560px] min-w-0',
        'focus-visible:outline-2 focus-visible:outline-accent',
        'hover:-translate-y-0.5 hover:border-accent-line',
      )}
    >
      <div className="flex items-start gap-3">
        <span className="icon-chip text-text-secondary group-hover:text-accent-ink h-8 w-8 shrink-0 transition-colors duration-150">
          <Icon size={15} />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <h3 className="text-[13px] font-medium text-text truncate">{tool.label}</h3>
            {tool.badge === 'danger' && <RiskBadge />}
            {tool.badge === 'admin' && <AdminBadge />}
          </div>
          <p className="mt-0.5 text-[11.5px] leading-[1.45] text-text-tertiary line-clamp-2">
            {tool.description}
          </p>
        </div>

        <div className="flex flex-col items-center gap-1 shrink-0 -mr-1 -mt-0.5">
          <button
            onClick={(e) => { e.stopPropagation(); onTogglePin() }}
            aria-label={pinned ? `Unpin ${tool.label}` : `Pin ${tool.label}`}
            title={pinned ? 'Unpin' : 'Pin to sidebar'}
            className={cn(
              'p-1 rounded transition-colors duration-150',
              pinned
                ? 'text-accent-ink hover:text-accent'
                : 'text-text-tertiary/50 hover:text-text-secondary opacity-0 group-hover:opacity-100 focus-visible:opacity-100',
            )}
          >
            <Star size={13} fill={pinned ? 'currentColor' : 'none'} />
          </button>
          <ArrowRight
            size={13}
            className="text-text-tertiary opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-150"
          />
        </div>
      </div>
    </div>
  )
}

function RiskBadge() {
  return (
    <span
      title="Aggressive tuning. A restore point is taken first."
      className="inline-flex items-center gap-1 text-[10px] font-medium text-red bg-red-dim px-1.5 py-px rounded shrink-0"
    >
      <AlertTriangle size={9} />
      risky
    </span>
  )
}

function AdminBadge() {
  return (
    <span
      title="Needs Administrator privileges"
      className="inline-flex items-center gap-1 text-[10px] font-medium text-yellow bg-yellow-dim px-1.5 py-px rounded shrink-0"
    >
      <ShieldAlert size={9} />
      admin
    </span>
  )
}
