import { Globe, Info } from 'lucide-react'
import { PageHero } from '../ui/PageHero'
import { Card } from '../ui/Card'
import { Skeleton } from '../ui/Skeleton'
import type { SystemInfo } from '../../types'

/**
 * Browser/shell extension management has no backend in this build. The
 * previous screen rendered a hardcoded catalog and reported install, toggle,
 * update and sync actions that never ran — a fake feature. It was removed
 * rather than kept as decoration; this page now states exactly what Optinix
 * can and cannot see.
 */
export default function ExtensionsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  if (!systemInfo) {
    return (
      <div className="page space-y-6">
        <Skeleton variant="text" width="220px" height="30px" />
        <Skeleton variant="rectangular" height="180px" />
      </div>
    )
  }

  return (
    <div className="page space-y-6">
      <PageHero
        title="Extensions"
        subtitle="Browser and shell extensions"
        icon={<Globe size={19} />}
        actions={<span className="px-3 py-1 rounded-full bg-surface-3 text-text-tertiary text-xs font-medium">Not available</span>}
      />

      <Card padding="lg">
        <div className="flex items-start gap-3 max-w-[78ch]">
          <span className="p-2 rounded-lg bg-surface-2 text-text-tertiary shrink-0">
            <Info size={16} />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-text">Optinix does not inspect extensions</h2>
            <p className="mt-1.5 text-[12.5px] text-text-secondary leading-relaxed">
              There is no browser-profile or shell-extension scanner in the backend, so this build
              cannot list, install, enable, disable or remove extensions. Nothing here is simulated:
              the previous catalog and its actions were removed rather than left as a mock.
            </p>
            <p className="mt-2 text-[12px] text-text-tertiary leading-relaxed">
              Use the extension manager built into each browser for that job. Optinix pages that do
              have a real backend behind them — Plugins, Marketplace and Developer Tools — are in the
              same sidebar group.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}
