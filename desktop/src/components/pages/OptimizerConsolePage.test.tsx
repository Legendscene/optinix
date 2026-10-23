import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OptimizerConsolePage } from './OptimizerConsolePage'
import type { Overview, OptimizeRun } from '../../types'

/* The optimizer console is the activation screen: it must drive the real
   optimize backend, show only measured results, and stay honest on failures. */
vi.mock('../../lib/api', () => ({
  api: {
    overview: vi.fn(),
    presets: vi.fn(),
    optimizeQuick: vi.fn(),
    speedTestPing: vi.fn(),
    gameProfiles: vi.fn(),
    installedGames: vi.fn(),
    detectGame: vi.fn(),
    applyGameProfile: vi.fn(),
    revertGameProfile: vi.fn(),
  },
}))

import { api } from '../../lib/api'

const ok = <T,>(value: T) => Promise.resolve(value)

const mockOverview = (overrides: Partial<Overview> = {}): Overview => ({
  generated_at: Date.now(),
  is_admin: true,
  health: { overall: 80, scores: {} },
  vitals: {
    cpu_percent: 12, cpu_temp: 50, cpu_threads: 12, cpu_cores: 6,
    ram_percent: 89, ram_used_gb: 13.6, ram_total_gb: 15.3, ram_available_gb: 1.7,
    swap_percent: 4, disk_percent: 86, disk_free_gb: 65.9, disk_total_gb: 476,
    process_count: 214, network_down_kbs: 0, network_up_kbs: 0, uptime_hours: 12,
    gpu: { name: 'GTX 1650', usage: 5, temperature: 51, memory_used: 1, memory_total: 4 },
    power_plan: { name: 'Balanced', is_high_performance: false },
    is_laptop: false, battery: null, is_admin: true, detected_game: null,
  },
  detected_game: null,
  actions: [],
  reclaimable: { total_bytes: 5.9 * 1024 ** 3, categories: [] },
  last_optimization: null,
  ...overrides,
})

const mockRun = (overrides: Partial<OptimizeRun> = {}): OptimizeRun => ({
  preset: 'balanced',
  name: 'Balanced',
  is_admin: true,
  steps: [
    { id: 'ram', label: 'Free memory', success: true, message: 'ok', duration_ms: 120 },
    { id: 'startup', label: 'Trim startup', success: true, message: 'ok', duration_ms: 40 },
  ],
  succeeded: 2,
  total: 2,
  before: { ram_percent: 89, ram_used_gb: 13.6, ram_available_gb: 1.7, process_count: 214, disk_free_gb: 65.9, cpu_percent: 12, timestamp: 0 },
  after: { ram_percent: 80, ram_used_gb: 12.4, ram_available_gb: 2.9, process_count: 198, disk_free_gb: 65.9, cpu_percent: 9, timestamp: 0 },
  deltas: { ram_used_gb: -1.2, ram_available_gb: 1.2, process_count: -16, disk_free_gb: 0 },
  ...overrides,
})

const fakeLibrary = {
  favorites: [], recents: [], gameFavorites: [],
  isFavorite: () => false,
  toggleFavorite: () => {},
  isGameFavorite: () => false,
  toggleGameFavorite: () => {},
  addRecent: () => {},
} as never

describe('OptimizerConsolePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview()))
    vi.mocked(api.presets).mockReturnValue(ok({
      presets: [
        { id: 'balanced', name: 'Balanced', summary: 'Clears caches, applies safe network tuning and trims memory.', detail: [], categories: [], post: [] },
        { id: 'gaming', name: 'Gaming', summary: 'For competitive play.', detail: [], categories: [], post: [] },
      ],
    }))
    vi.mocked(api.speedTestPing).mockReturnValue(ok({ host: '1.1.1.1', avg_ms: 9, min_ms: 8, max_ms: 11, packet_loss: 0, samples: 4 }))
    vi.mocked(api.gameProfiles).mockReturnValue(ok({
      profiles: [
        { id: 'warzone', name: 'Call of Duty: Warzone', description: 'High FPS for fast-paced combat', builtin: true },
        { id: 'valorant', name: 'Valorant', description: 'Competitive FPS — max frames, min input lag', builtin: true },
        { id: 'cs2', name: 'Counter-Strike 2', description: 'Low latency competitive profile', builtin: true },
        { id: 'fortnite', name: 'Fortnite', description: 'High FPS for building/editing responsiveness', builtin: true },
      ],
    }))
    /* Default scan: all three mock profiles installed; only cs2 has an appid
       (Steam), so cover-art behaviour is exercised in both branches. */
    vi.mocked(api.installedGames).mockReturnValue(ok({
      matched: [
        { profile_id: 'valorant', source: 'registry' },
        { profile_id: 'cs2', source: 'steam', appid: 730 },
        { profile_id: 'fortnite', source: 'registry' },
      ],
      others: [],
    }))
    vi.mocked(api.detectGame).mockReturnValue(ok({ detected: false }))
    vi.mocked(api.applyGameProfile).mockReturnValue(ok({ results: [{ success: true, message: 'profile applied' }] }))
    vi.mocked(api.revertGameProfile).mockReturnValue(ok({ results: [{ success: true, message: 'profile reverted' }] }))
  })

  it('renders the ExitLag-style console with real read-outs and tools', async () => {
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    expect(screen.getByRole('heading', { name: /optimize your system/i })).toBeInTheDocument()
    /* Real values from the overview payload, never invented ones. */
    expect(await screen.findByText('1.7')).toBeInTheDocument()
    expect(screen.getByText(`${Math.round(9)}`)).toBeInTheDocument()
    /* Tool grid comes from the real nav registry; the card and its pin
       control share the accessible name, so both rendering is expected. */
    expect(screen.getAllByRole('button', { name: /One Click Optimize/i }).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByRole('button', { name: /Cleanup/i }).length).toBeGreaterThanOrEqual(1)
  })

  it('activates the backend with the chosen preset and shows measured results', async () => {
    const user = userEvent.setup()
    vi.mocked(api.optimizeQuick).mockReturnValue(ok(mockRun()))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    await user.click(await screen.findByRole('button', { name: /Activate/i }))
    expect(await screen.findByText(/Balanced finished/)).toBeInTheDocument()
    expect(api.optimizeQuick).toHaveBeenCalledWith('balanced')
    /* The real deltas are shown: RAM available +1.2 GB, processes -16. */
    expect(screen.getByText(/RAM available \+1\.20 GB/)).toBeInTheDocument()
    expect(screen.getByText(/Processes -16/)).toBeInTheDocument()
    /* The count is split across text nodes in JSX, so match the fragment. */
    expect(screen.getByText('2/2')).toBeInTheDocument()
    expect(screen.getByText(/steps applied/)).toBeInTheDocument()
  })

  it('switches presets and passes the new one through', async () => {
    const user = userEvent.setup()
    vi.mocked(api.optimizeQuick).mockReturnValue(ok(mockRun({ preset: 'gaming', name: 'Gaming' })))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    await user.click(await screen.findByRole('radio', { name: 'Gaming' }))
    await user.click(screen.getByRole('button', { name: /Activate/i }))
    expect(await screen.findByText(/Gaming finished/)).toBeInTheDocument()
    expect(api.optimizeQuick).toHaveBeenCalledWith('gaming')
  })

  it('stays honest when the optimization backend fails', async () => {
    const user = userEvent.setup()
    vi.mocked(api.optimizeQuick).mockRejectedValue(new Error('/api/optimize/quick: 403'))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    await user.click(await screen.findByRole('button', { name: /Activate/i }))
    expect(await screen.findByText('The optimization did not complete')).toBeInTheDocument()
    expect(screen.getByText('/api/optimize/quick: 403')).toBeInTheDocument()
    /* No step is invented as successful. */
    expect(screen.queryByText(/finished/)).not.toBeInTheDocument()
  })

  it('warns about limited mode with the non-admin payload and keeps working', async () => {
    const user = userEvent.setup()
    vi.mocked(api.overview).mockReturnValue(ok(mockOverview({ vitals: undefined as never })))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    /* No overview data: the console still renders with dashes, no crash. */
    await waitFor(() => expect(screen.getByRole('button', { name: /Activate/i })).toBeInTheDocument())
    expect(screen.getByText(/Checking session privileges/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Activate/i }))
    expect(api.optimizeQuick).toHaveBeenCalled()
  })

  it('lists game profiles and leads with the detected game', async () => {
    vi.mocked(api.detectGame).mockReturnValue(ok({ detected: true, game_id: 'cs2', game_name: 'Counter-Strike 2' }))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    /* Game-card headings are uniquely named; tool cards share the h4 role. */
    const cs2 = await screen.findByRole('heading', { name: 'Counter-Strike 2' })
    const valorant = screen.getByRole('heading', { name: 'Valorant' })
    const fortnite = screen.getByRole('heading', { name: 'Fortnite' })
    /* The detected game leads: it must appear in the DOM before the others. */
    expect(cs2.compareDocumentPosition(valorant) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(cs2.compareDocumentPosition(fortnite) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    const cs2Card = cs2.closest<HTMLElement>('.surface-card')!
    /* The detection marker is the only claim the page makes about a live game. */
    expect(cs2Card).toHaveTextContent('Running now')
    expect(cs2Card).toHaveClass('border-eg-line')
  })

  it('applies a profile through the real backend and shows its result feed', async () => {
    const user = userEvent.setup()
    vi.mocked(api.applyGameProfile).mockReturnValue(ok({ results: [{ success: true, message: 'Valorant profile applied' }] }))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    const valorantHeading = await screen.findByRole('heading', { name: 'Valorant' })
    const card = valorantHeading.closest<HTMLElement>('.surface-card')!
    await user.click(within(card).getByRole('button', { name: /Apply profile/i }))

    expect(api.applyGameProfile).toHaveBeenCalledWith('valorant')
    expect(await screen.findByText('Valorant profile applied')).toBeInTheDocument()
    expect(within(card).getByRole('button', { name: /Revert/i })).toBeInTheDocument()
  })

  it('stays honest when profile apply is rejected', async () => {
    const user = userEvent.setup()
    vi.mocked(api.applyGameProfile).mockRejectedValue(new Error('/api/game-profiles/apply: 403'))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    const valorantHeading = await screen.findByRole('heading', { name: 'Valorant' })
    await user.click(within(valorantHeading.closest<HTMLElement>('.surface-card')!).getByRole('button', { name: /Apply profile/i }))

    expect(await screen.findByText('/api/game-profiles/apply: 403')).toBeInTheDocument()
    /* A rejected apply must not leave a Revert (applied) state behind. */
    expect(within(valorantHeading.closest<HTMLElement>('.surface-card')!).queryByRole('button', { name: /Revert/i })).not.toBeInTheDocument()
  })

  it('reverts the applied profile through the backend', async () => {
    const user = userEvent.setup()
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    const valorantHeading = await screen.findByRole('heading', { name: 'Valorant' })
    const card = valorantHeading.closest<HTMLElement>('.surface-card')!
    await user.click(within(card).getByRole('button', { name: /Apply profile/i }))
    await user.click(await within(card).findByRole('button', { name: /Revert/i }))

    expect(api.revertGameProfile).toHaveBeenCalled()
    expect(await within(card).findByText('profile reverted')).toBeInTheDocument()
    expect(within(card).getByRole('button', { name: /Apply profile/i })).toBeInTheDocument()
  })

  it('shows the honest empty state when nothing is installed (full profiles are NOT shown)', async () => {
    vi.mocked(api.installedGames).mockReturnValue(ok({ matched: [], others: [] }))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    expect(await screen.findByText(/No games detected on this PC/)).toBeInTheDocument()
    /* The page never silently falls back to the full profile list. */
    expect(screen.queryByRole('heading', { name: 'Valorant' })).not.toBeInTheDocument()
  })

  it('gives the detected game cover art from the detection response', async () => {
    vi.mocked(api.detectGame).mockReturnValue(ok({ detected: true, game_id: 'warzone', game_name: 'Call of Duty: Warzone', appid: 1938090 }))
    vi.mocked(api.installedGames).mockReturnValue(ok({ matched: [], others: [] }))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    const card = (await screen.findByRole('heading', { name: 'Call of Duty: Warzone' })).closest<HTMLElement>('.surface-card')!
    expect(card).toHaveTextContent('Running now')
    const img = card.querySelector('img')
    expect(img).not.toBeNull()
    expect(img!.getAttribute('src')).toContain('steam/apps/1938090')
  })

  it('renders Steam cover art when the scan carries an appid, tile otherwise', async () => {
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    const cs2 = await screen.findByRole('heading', { name: 'Counter-Strike 2' })
    const cs2Card = cs2.closest<HTMLElement>('.surface-card')!
    const img = cs2Card.querySelector('img')
    expect(img).not.toBeNull()
    expect(img!.getAttribute('src')).toContain('steam/apps/730')

    const valorant = screen.getByRole('heading', { name: 'Valorant' })
    const vCard = valorant.closest<HTMLElement>('.surface-card')!
    expect(vCard.querySelector('img')).toBeNull()
    expect(vCard).toHaveTextContent('V')  /* initial-tile fallback */
  })

  it('lists installed games that have no profile as proper cards with covers', async () => {
    vi.mocked(api.installedGames).mockReturnValue(ok({
      matched: [{ profile_id: 'cs2', source: 'steam', appid: 730 }],
      others: [{ name: 'Wuthering Waves', source: 'steam', appid: 3513350 }],
    }))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    expect(await screen.findByText('Wuthering Waves')).toBeInTheDocument()
    /* The profile-less game sits in the same card grid, with a real cover. */
    const card = screen.getByText('Wuthering Waves').closest<HTMLElement>('.surface-card')!
    const img = card.querySelector('img')
    expect(img).not.toBeNull()
    expect(img!.getAttribute('src')).toContain('steam/apps/3513350')
    expect(card).toHaveTextContent('No profile yet')
    /* It is informational only — no Apply/Revert controls may sneak in. */
    expect(card.querySelector('button')).toBeNull()
  })

  it('shows the preset plan as queued steps with an indeterminate bar while the run is in flight', async () => {
    const user = userEvent.setup()
    /* A deferred promise: the request stays in flight until the test resolves
       it, so the busy-state UI can be inspected for real. */
    let resolveRun: (v: OptimizeRun) => void = () => {}
    vi.mocked(api.optimizeQuick).mockImplementation(() => new Promise((res) => { resolveRun = res }))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    await user.click(await screen.findByRole('button', { name: /Activate/i }))

    /* The queued rows are exactly the preset's plan — the mock balanced
       preset carries categories/post directly from the backend. */
    expect(screen.getByText(/is running/)).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: /Balanced optimization progress/i })).toBeInTheDocument()
    /* The preset rails null categories/post, so the plan is empty here; a
       lens preset exercises the real plan render. */
    await user.click(await screen.findByRole('radio', { name: 'Gaming' }))
    expect(await screen.findByText('Gaming is running…')).toBeInTheDocument()
    const bar = screen.getByRole('progressbar').firstElementChild as HTMLElement
    expect(bar.getAttribute('data-indeterminate')).toBe('true')

    /* Landing the response resolves the run; the queued steps vanish in
       favour of real outcomes. */
    resolveRun(mockRun({ preset: 'gaming', name: 'Gaming' }))
    expect(await screen.findByText(/Gaming finished/)).toBeInTheDocument()
    expect(screen.queryByText(/is running/)).not.toBeInTheDocument()
    /* The bar is now tied to the actual fraction and is no longer
       indeterminate. */
    const settled = screen.getByRole('progressbar')
    expect(settled.getAttribute('aria-valuenow')).toBe('100')
    expect((settled.firstElementChild as HTMLElement).getAttribute('data-indeterminate')).toBeNull()
  })

  it('keeps a failed step red through the settle and lowers the fill accordingly', async () => {
    const user = userEvent.setup()
    const failed = mockRun({
      succeeded: 1,
      steps: [
        { id: 'ram', label: 'Free memory', success: true, message: 'ok', duration_ms: 100 },
        { id: 'startup', label: 'Trim startup', success: false, message: 'requires admin', duration_ms: 10 },
      ],
    })
    let resolveRun: (v: OptimizeRun) => void = () => {}
    vi.mocked(api.optimizeQuick).mockImplementation(() => new Promise((res) => { resolveRun = res }))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    await user.click(await screen.findByRole('button', { name: /Activate/i }))
    resolveRun(failed)
    expect(await screen.findByText(/Balanced finished/)).toBeInTheDocument()
    /* The count lives in its own tnum span between text fragments. */
    expect(screen.getByText('1/2')).toBeInTheDocument()

    /* The failed step keeps the fail icon and its real message — never
       quietly converted into a success. */
    const startupRow = screen.getByText('Trim startup').closest('li')!
    expect(startupRow.querySelector('svg')).toHaveClass('text-red')
    expect(startupRow).toHaveTextContent('requires admin')

    /* The fill reports only real successes: 1 of 2 = 50%, not 100. */
    const bar = screen.getByRole('progressbar')
    expect(bar.getAttribute('aria-valuenow')).toBe('50')
    expect((bar.firstElementChild as HTMLElement).style.width).toBe('50%')
  })

  it('shows the section error state when the scan fails', async () => {
    vi.mocked(api.installedGames).mockRejectedValue(new Error('/api/game-profiles/installed: 500'))
    render(<OptimizerConsolePage onNavigate={() => {}} library={fakeLibrary} />)

    expect(await screen.findByText(/Could not scan for installed games/)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Valorant' })).not.toBeInTheDocument()
  })
})
