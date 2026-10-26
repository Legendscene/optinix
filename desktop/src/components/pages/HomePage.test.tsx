import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HomePage } from './HomePage'
import type { Overview } from '../../types'

/* Mock the API module: HomePage must work with real data shapes and must
   render honest placeholders when a sensor is missing. */
vi.mock('../../lib/api', () => ({
  api: {
    overview: vi.fn(),
    presets: vi.fn(),
    gameProfiles: vi.fn(),
    installedGames: vi.fn(),
    timelineEvents: vi.fn(),
    applyGameProfile: vi.fn(),
    speedTestPing: vi.fn(),
    optimizeQuick: vi.fn(),
  },
}))

import { api } from '../../lib/api'

const mockOverview = (overrides: Partial<Overview> = {}): Overview => ({
  generated_at: Date.now(),
  is_admin: true,
  health: { overall: 92, scores: {} },
  vitals: {
    cpu_percent: 34,
    cpu_temp: 52,
    cpu_threads: 16,
    cpu_cores: 8,
    ram_percent: 61,
    ram_used_gb: 19.5,
    ram_total_gb: 32,
    ram_available_gb: 12.5,
    swap_percent: 4,
    disk_percent: 71,
    disk_free_gb: 340,
    disk_total_gb: 953,
    process_count: 214,
    network_down_kbs: 1250,
    network_up_kbs: 180,
    uptime_hours: 30,
    gpu: { name: 'NVIDIA RTX 4070', usage: 41, temperature: 64, memory_used: 4, memory_total: 12 },
    power_plan: { name: 'Balanced', is_high_performance: false },
    is_laptop: false,
    battery: null,
    is_admin: true,
    detected_game: null,
  },
  detected_game: null,
  actions: [],
  reclaimable: null,
  last_optimization: null,
  ...overrides,
})

const ok = <T,>(value: T) => Promise.resolve(value)

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.presets).mockReturnValue(ok({ presets: [{ id: 'balanced', name: 'Balanced', summary: 'Safe pass', detail: [], categories: [], post: [] }] }))
    vi.mocked(api.gameProfiles).mockReturnValue(ok({ profiles: [] }))
    vi.mocked(api.installedGames).mockReturnValue(ok({ matched: [], others: [] }))
    vi.mocked(api.timelineEvents).mockReturnValue(ok({ events: [] }))
  })

  it('renders real vitals from the overview payload', async () => {
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview()))
    render(<HomePage onNavigate={() => {}} />)

    await waitFor(() => expect(screen.getByText('34%')).toBeInTheDocument())
    /* RAM shown as real used/total, not a fabricated number. */
    expect(screen.getByText('19.5 / 32 GB')).toBeInTheDocument()
    expect(screen.getByText('340 GB free')).toBeInTheDocument()
    /* GPU present -> real name, no "not detected" fallback. */
    expect(screen.getByText('NVIDIA RTX 4070')).toBeInTheDocument()
  })

  it('shows honest placeholders when the GPU cannot be read', async () => {
    const d = mockOverview()
    d.vitals.gpu = { name: 'N/A', usage: null, temperature: null, memory_used: 0, memory_total: 0 }
    vi.mocked(api.overview).mockReturnValue(ok(d))
    render(<HomePage onNavigate={() => {}} />)

    await waitFor(() => expect(screen.getByText('Not detected')).toBeInTheDocument())
    /* The GPU card is addressed by its hint title; inside it the value must
       be the honest dash, not a number. The hint also explains why. */
    const gpuCard = screen.getByTitle(/No readable GPU load/)
    expect(within(gpuCard).getByText('—')).toBeInTheDocument()
    /* Never invents a GPU percentage. */
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
  })

  it('renders the backend error state when the service is unreachable', async () => {
    vi.mocked(api.overview).mockRejectedValue(new Error('fetch failed'))
    render(<HomePage onNavigate={() => {}} />)

    await waitFor(() =>
      expect(screen.getByText('Could not reach the Optinix service')).toBeInTheDocument(),
    )
    expect(screen.getByText('fetch failed')).toBeInTheDocument()
  })

  it('offers the primary action from real presets and runs it', async () => {
    const user = userEvent.setup()
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview()))
    vi.mocked(api.optimizeQuick).mockReturnValue(ok({
      preset: 'balanced',
      name: 'Balanced',
      is_admin: true,
      steps: [{ id: 's1', label: 'Cleanup', success: true, message: 'ok', duration_ms: 12 }],
      succeeded: 1,
      total: 1,
      before: {} as never,
      after: {} as never,
      deltas: { ram_used_gb: 0, ram_available_gb: 0, process_count: 0, disk_free_gb: 0 },
    }))
    render(<HomePage onNavigate={() => {}} />)

    const button = await screen.findByRole('button', { name: /Optimize now/ })
    await user.click(button)
    await waitFor(() =>
      expect(screen.getByText(/Balanced complete — 1\/1 steps applied/)).toBeInTheDocument(),
    )
  })

  it('shows the honest empty state when nothing needs attention', async () => {
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview()))
    render(<HomePage onNavigate={() => {}} />)

    await waitFor(() =>
      expect(screen.getByText('Everything looks good')).toBeInTheDocument(),
    )
    expect(screen.getByText('Nothing needs attention')).toBeInTheDocument()
  })

  it('lists only verified installed games, never the whole profile catalog', async () => {
    const profiles = [
      { id: 'warzone', name: 'Call of Duty: Warzone', description: 'High FPS for fast-paced combat', builtin: true },
      { id: 'cs2', name: 'Counter-Strike 2', description: 'Low latency competitive profile', builtin: true },
    ]
    vi.mocked(api.gameProfiles).mockReturnValue(ok({ profiles }))
    vi.mocked(api.installedGames).mockReturnValue(ok({
      matched: [{ profile_id: 'cs2', source: 'steam', appid: 730, status: 'verified_installed' as const }],
      others: [],
      unverified: [{ profile_id: 'warzone', source: 'registry', status: 'missing' as const }],
    }))
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview()))
    render(<HomePage onNavigate={() => {}} />)

    /* The verified game is listed; the uninstalled profile is not — even
       though the profile catalog contains it. */
    expect(await screen.findByText('Counter-Strike 2')).toBeInTheDocument()
    expect(screen.queryByText('Call of Duty: Warzone')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Apply Call of Duty: Warzone profile/ })).not.toBeInTheDocument()
    /* The catalog is described honestly instead of being rendered as games. */
    expect(screen.getByText(/2 supported profiles ship with Optinix/)).toBeInTheDocument()
  })

  it('shows an honest empty state when no installation is verified', async () => {
    vi.mocked(api.gameProfiles).mockReturnValue(ok({ profiles: [
      { id: 'warzone', name: 'Call of Duty: Warzone', description: 'High FPS', builtin: true },
    ] }))
    vi.mocked(api.installedGames).mockReturnValue(ok({ matched: [], others: [] }))
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview()))
    render(<HomePage onNavigate={() => {}} />)

    expect(await screen.findByText('No games verified on this PC.')).toBeInTheDocument()
    expect(screen.queryByText('Call of Duty: Warzone')).not.toBeInTheDocument()
  })

  it('shows a verified install with no profile, but offers no Apply action', async () => {
    vi.mocked(api.gameProfiles).mockReturnValue(ok({ profiles: [
      { id: 'warzone', name: 'Call of Duty: Warzone', description: 'High FPS', builtin: true },
    ] }))
    vi.mocked(api.installedGames).mockReturnValue(ok({
      matched: [],
      others: [{ name: 'Wuthering Waves', source: 'steam', status: 'verified_installed' as const, appid: 3513350 }],
    }))
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview()))
    render(<HomePage onNavigate={() => {}} />)

    expect(await screen.findByText('Wuthering Waves')).toBeInTheDocument()
    expect(screen.getByText('Installed — no optimization profile yet')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Apply/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/No games verified on this PC/)).not.toBeInTheDocument()
  })

  it('shows only the backend-verified running game, with process evidence', async () => {
    vi.mocked(api.gameProfiles).mockReturnValue(ok({ profiles: [
      { id: 'warzone', name: 'Call of Duty: Warzone', description: 'High FPS for fast-paced combat', builtin: true },
    ] }))
    vi.mocked(api.installedGames).mockReturnValue(ok({ matched: [], others: [] }))
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview({
      detected_game: {
        id: 'warzone',
        name: 'Call of Duty: Warzone',
        description: 'High FPS for fast-paced combat',
        state: 'running',
        verified: true,
        evidence: { pid: 42, exe: 'C:\\Games\\cod.exe' },
      },
    })))
    render(<HomePage onNavigate={() => {}} />)

    expect((await screen.findAllByText('Call of Duty: Warzone')).length).toBeGreaterThan(0)
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByTitle(/C:\\Games\\cod.exe/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Apply/i }).length).toBeGreaterThan(0)
  })

  it('does not trust an unverified detected game from a stale payload', async () => {
    vi.mocked(api.gameProfiles).mockReturnValue(ok({ profiles: [
      { id: 'warzone', name: 'Call of Duty: Warzone', description: 'High FPS', builtin: true },
    ] }))
    vi.mocked(api.installedGames).mockReturnValue(ok({ matched: [], others: [] }))
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview({
      detected_game: {
        id: 'warzone', name: 'Call of Duty: Warzone', description: 'High FPS', verified: false,
      },
    })))
    render(<HomePage onNavigate={() => {}} />)

    await waitFor(() => expect(screen.getByText('34%')).toBeInTheDocument())
    expect(screen.queryByText('Call of Duty: Warzone')).not.toBeInTheDocument()
  })

  it('does not fall back to the profile catalog when the install scan fails', async () => {
    /* Production mode must fail honest, not populate the dashboard with
       profiles that were never verified on this machine. */
    vi.mocked(api.gameProfiles).mockReturnValue(ok({ profiles: [
      { id: 'warzone', name: 'Call of Duty: Warzone', description: 'High FPS', builtin: true },
    ] }))
    vi.mocked(api.installedGames).mockRejectedValue(new Error('scan failed'))
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview()))
    render(<HomePage onNavigate={() => {}} />)

    expect(await screen.findByText("Could not read this PC's installed games.")).toBeInTheDocument()
    expect(screen.queryByText('Call of Duty: Warzone')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Apply/i })).not.toBeInTheDocument()
  })

  it('navigates when an action row is clicked', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    const d = mockOverview({
      actions: [{
        id: 'disk_pressure',
        title: 'System drive is nearly full',
        detail: '86% used, 120 GB free. Clean up to reclaim space.',
        severity: 'high',
        page: 'cleanup',
        action: null,
        meta: {},
      }],
    })
    vi.mocked(api.overview).mockReturnValue(ok(d))
    render(<HomePage onNavigate={onNavigate} />)

    const row = await screen.findByRole('button', { name: /System drive is nearly full/ })
    await user.click(row)
    expect(onNavigate).toHaveBeenCalledWith('cleanup')
  })
})
