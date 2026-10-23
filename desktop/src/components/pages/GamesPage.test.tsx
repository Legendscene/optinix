import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GamesPage } from './GamesPage'
import type { GameLibrary, GameScanProgress } from '../../types'

/* The Games page is the library of real installations. These tests pin the
   honesty contract: only verified games are listed by default, the default
   view is installed-only, and every state is driven by the backend response
   rather than invented. */
vi.mock('../../lib/api', () => ({
  api: {
    gameLibrary: vi.fn(),
    gameLibraryScan: vi.fn(),
    gameLibraryProgress: vi.fn(),
    gameLibraryCancel: vi.fn(),
    gameLibraryRoots: vi.fn(),
    gameLibraryAddRoot: vi.fn(),
    gameLibraryRemoveRoot: vi.fn(),
    gameLibraryOpen: vi.fn(),
    gameLibraryLaunch: vi.fn(),
    gameLibraryRunning: vi.fn(),
    gameLibraryFavorites: vi.fn(),
    gameLibraryFavoriteAdd: vi.fn(),
    gameLibraryFavoriteRemove: vi.fn(),
    gameLibrarySession: vi.fn(),
    gameLibraryEmulators: vi.fn(),
    gameLibraryAddEmulator: vi.fn(),
    gameLibraryRemoveEmulator: vi.fn(),
    gameLibraryManual: vi.fn(),
    gameLibraryResolveShortcut: vi.fn(),
    gameLibraryScanFolder: vi.fn(),
    gameLibraryAddExe: vi.fn(),
    gameLibraryAddFolder: vi.fn(),
    gameLibraryUpdateManual: vi.fn(),
    gameLibraryRemoveManual: vi.fn(),
    gameLibraryManualLaunch: vi.fn(),
  },
}))

import { api } from '../../lib/api'

const ok = <T,>(v: T) => Promise.resolve(v)

type GOver = Partial<GameLibrary['games'][number]>
const g = (over: GOver): GameLibrary['games'][number] => ({
  id: 'steam:1',
  name: 'Half-Life 2',
  source: 'steam',
  install_path: 'C:/Games/HalfLife2',
  exe_path: 'C:/Games/HalfLife2/hl2.exe',
  status: 'installed',
  ...over,
})

const makeLibrary = (over: Partial<GameLibrary> = {}): GameLibrary => ({
  games: [g({})],
  notes: [],
  scanned_at: 1700000000,
  needs_scan: false,
  ...over,
})

describe('GamesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary()))
    vi.mocked(api.gameLibraryProgress).mockReturnValue(
      ok({ running: false, fraction: 1, games_found: 1, cancel_requested: false } satisfies GameScanProgress),
    )
    vi.mocked(api.gameLibraryRoots).mockReturnValue(ok({ roots: [] }))
    vi.mocked(api.gameLibraryScan).mockReturnValue(ok({ started: true }))
    vi.mocked(api.gameLibraryCancel).mockReturnValue(ok({ cancelled: true }))
    vi.mocked(api.gameLibraryFavorites).mockReturnValue(ok({ favorites: [] }))
    vi.mocked(api.gameLibraryFavoriteAdd).mockReturnValue(ok({ favorites: ['steam:1'] }))
    vi.mocked(api.gameLibraryFavoriteRemove).mockReturnValue(ok({ favorites: [] }))
    vi.mocked(api.gameLibrarySession).mockReturnValue(new Promise(() => { /* pending */ }))
    vi.mocked(api.gameLibraryEmulators).mockReturnValue(ok({ emulators: [] }))
    vi.mocked(api.gameLibraryAddEmulator).mockReturnValue(ok({ emulator: { id: 'emu:1', name: 'BlueStacks', exe_path: 'C:/emu/HD-Player.exe', args: '', added_at: 0 } }))
    vi.mocked(api.gameLibraryRemoveEmulator).mockReturnValue(ok({ removed: 'emu:1' }))
    vi.mocked(api.gameLibraryScanFolder).mockReturnValue(ok({ folder: 'C:/Games/X', candidates: [{ path: 'C:/Games/X/GameClient.exe', name: 'GameClient', size_mb: 80 }] }))
    vi.mocked(api.gameLibraryAddExe).mockReturnValue(ok({ game: { id: 'manual:x', name: 'Manual Game', exe_path: 'C:/Games/X/x.exe', args: '', source: 'manual', added_at: 0, status: 'installed', label: 'manually added' }, updated: false }))
    vi.mocked(api.gameLibraryAddFolder).mockReturnValue(ok({ game: { id: 'manualfolder:x', name: 'Folder Game', exe_path: 'C:/Games/X/GameClient.exe', args: '', folder: 'C:/Games/X', source: 'manual', added_at: 0, status: 'installed', label: 'manually added' }, updated: false }))
    vi.mocked(api.gameLibraryRemoveManual).mockReturnValue(ok({ removed: 'manual:x' }))
    vi.mocked(api.gameLibraryManualLaunch).mockReturnValue(ok({ created: true, pid: 1 }))
    vi.mocked(api.gameLibraryResolveShortcut).mockReturnValue(ok({ target: 'C:/Games/RealGame.exe', args: '', exists: true }))
  })

  it('keeps discovered emulator shells out of Native and shows the Emulator badge', async () => {
    const user = userEvent.setup()
    vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
      games: [
        g({}),
        g({
          id: 'startmenu:msi-app-player',
          name: 'MSI App Player',
          source: 'startmenu',
          install_path: 'C:/Program Files (x86)/BlueStacks X_msi5',
          exe_path: 'C:/Program Files (x86)/BlueStacks X_msi5/MSI App Player.exe',
          kind: 'emulator',
        }),
      ],
    })))
    render(<GamesPage />)
    expect(await screen.findByText('MSI App Player')).toBeInTheDocument()
    /* Discovered emulator shells carry a visible badge on the card. */
    expect(screen.getByText('Emulator')).toBeInTheDocument()
    /* Native PC Games = native only — emulator shells are excluded. */
    await user.selectOptions(screen.getByRole('combobox', { name: /filter by library category/i }), 'native')
    expect(screen.queryByText('MSI App Player')).not.toBeInTheDocument()
    expect(screen.getByText('Half-Life 2')).toBeInTheDocument()
    /* Emulator Games groups both discovered shells and manual associations. */
    await user.selectOptions(screen.getByRole('combobox', { name: /filter by library category/i }), 'emulator')
    expect(screen.getByText('MSI App Player')).toBeInTheDocument()
    expect(screen.queryByText('Half-Life 2')).not.toBeInTheDocument()
  })

  it('shows the loading skeleton before the library resolves', () => {
    vi.mocked(api.gameLibrary).mockReturnValue(new Promise(() => { /* pending */ }))
    render(<GamesPage />)
    expect(screen.getByText('Gaming Center')).toBeInTheDocument()
    /* Skeleton pulse blocks exist — cards render later. */
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
  })

  it('renders the backend error state when the service is unreachable', async () => {
    vi.mocked(api.gameLibrary).mockRejectedValue(new Error('/api/game-library: 500'))
    render(<GamesPage />)
    expect(await screen.findByText('Could not load the game library')).toBeInTheDocument()
    expect(screen.getByText('/api/game-library: 500')).toBeInTheDocument()
  })

  it('shows the empty state and lets the user start a scan when nothing is detected', async () => {
    vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
      games: [],
      needs_scan: false,
      notes: ['Steam not found on this PC (checked default and registry paths).'],
    })))
    const user = userEvent.setup()
    render(<GamesPage />)
    expect(await screen.findByText('No installed games detected yet')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /run scan/i }))
    expect(api.gameLibraryScan).toHaveBeenCalled()
  })

  it('shows verified installed games with launcher, drive and status', async () => {
    const user = userEvent.setup()
    render(<GamesPage />)
    expect(await screen.findByText('Half-Life 2')).toBeInTheDocument()
    expect(screen.getByText('Installed')).toBeInTheDocument()
    /* The launcher label appears both in the filter options and on the card. */
    expect(screen.getAllByText('Steam').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('C:/Games/HalfLife2/hl2.exe')).toBeInTheDocument()
    /* Drive filter chips read the real install path */
    expect(screen.getAllByText('C:').length).toBeGreaterThanOrEqual(1)
    void user
  })

  it('shows every detected game by default with honest status pills', async () => {
    vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
      games: [
        g({}),
        g({ id: 'epic:9', name: 'Dangling Manifest', source: 'epic', status: 'missing' }),
        g({ id: 'xbox:3', name: 'Locked Package', source: 'xbox', status: 'restricted' }),
        g({ id: 'riot:1', name: 'Running Game', source: 'riot', status: 'running' }),
      ],
    })))
    const user = userEvent.setup()
    render(<GamesPage />)

    /* Nothing is hidden by default: a disconnected drive or a locked
       package still owns a card, honestly labeled. */
    expect(await screen.findByText('Half-Life 2')).toBeInTheDocument()
    expect(screen.getByText('Running Game')).toBeInTheDocument()
    expect(screen.getByText('Dangling Manifest')).toBeInTheDocument()
    expect(screen.getByText('Missing files')).toBeInTheDocument()
    expect(screen.getByText('Locked Package')).toBeInTheDocument()
    expect(screen.getByText('Access restricted')).toBeInTheDocument()

    /* The status filter can still narrow to installed-only. */
    await user.selectOptions(screen.getByLabelText(/filter by status/i), 'installed')
    expect(screen.queryByText('Dangling Manifest')).not.toBeInTheDocument()
    expect(screen.queryByText('Locked Package')).not.toBeInTheDocument()
    expect(screen.getByText('Half-Life 2')).toBeInTheDocument()
    expect(screen.getByText('Running Game')).toBeInTheDocument()
  })

  it('filters by launcher, drive and search together with real data', async () => {
    const user = userEvent.setup()
    vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
      games: [
        g({}),
        g({ id: 'epic:2', name: 'Another Epic Game', source: 'epic' }),
        g({ id: 'steam:3', name: 'Steam D-Drive', install_path: 'D:/Steam/steamapps/common/X', exe_path: 'D:/Steam/steamapps/common/X/game.exe' }),
      ],
    })))
    render(<GamesPage />)

    await screen.findByText('Half-Life 2')
    await user.selectOptions(screen.getByLabelText(/filter by launcher/i), 'epic')
    expect(screen.getByText('Another Epic Game')).toBeInTheDocument()
    expect(screen.queryByText('Half-Life 2')).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText(/filter by launcher/i), 'all')

    await user.selectOptions(screen.getByLabelText(/filter by installation drive/i), 'D:')
    expect(screen.getByText('Steam D-Drive')).toBeInTheDocument()
    expect(screen.queryByText('Half-Life 2')).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText(/filter by installation drive/i), 'all')

    await user.type(screen.getByLabelText(/search installed games/i), 'half')
    expect(screen.getByText('Half-Life 2')).toBeInTheDocument()
    expect(screen.queryByText('Another Epic Game')).not.toBeInTheDocument()
  })

  it('shows live scan progress and supports cancellation', async () => {
    /* The backend reports a running scan; the poll keeps the panel visible. */
    vi.mocked(api.gameLibraryProgress).mockReturnValue(
      ok({ running: true, fraction: 0.3, games_found: 5, cancel_requested: false } satisfies GameScanProgress),
    )
    const user = userEvent.setup()
    render(<GamesPage />)

    await user.click(await screen.findByRole('button', { name: /refresh scan/i }))
    expect(api.gameLibraryScan).toHaveBeenCalled()
    /* The busy panel with the real fraction appears (polled state). */
    const cancel = await screen.findByRole('button', { name: /cancel/i })
    await user.click(cancel)
    expect(api.gameLibraryCancel).toHaveBeenCalled()
  })

  it('opens an installation folder and reports the backend error honestly', async () => {
    const user = userEvent.setup()
    vi.mocked(api.gameLibraryOpen).mockRejectedValue(new Error('open: 400'))
    render(<GamesPage />)

    await user.click(await screen.findByRole('button', { name: /folder/i }))
    expect(api.gameLibraryOpen).toHaveBeenCalledWith('steam:1')
    expect(await screen.findByText('open: 400')).toBeInTheDocument()
  })

  it('launches a verified game after explicit user action', async () => {
    const user = userEvent.setup()
    vi.mocked(api.gameLibraryLaunch).mockReturnValue(ok({ launched: true }))
    render(<GamesPage />)

    await user.click(await screen.findByRole('button', { name: /launch/i }))
    expect(api.gameLibraryLaunch).toHaveBeenCalledWith('steam:1')
    expect(await screen.findByText(/Launched Half-Life 2/i)).toBeInTheDocument()
  })

  /* ---------------- Gaming Center additions (favorites & details) --------- */

  describe('favorites', () => {
    it('toggles a favorite through the backend-persisted endpoint', async () => {
      const user = userEvent.setup()
      render(<GamesPage />)
      await screen.findByText('Half-Life 2')
      await user.click(screen.getByRole('button', { name: /favorite half-life 2/i }))
      expect(api.gameLibraryFavoriteAdd).toHaveBeenCalledWith('steam:1')
      /* The star state is optimistic; the endpoint response is authoritative. */
      await user.click(screen.getByRole('button', { name: /unfavorite half-life 2/i }))
      expect(api.gameLibraryFavoriteRemove).toHaveBeenCalledWith('steam:1')
    })

    it('filters to favorites only when the favorites toggle is pressed', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibraryFavorites).mockReturnValue(ok({ favorites: ['steam:1'] }))
      vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
        games: [
          g({}),
          g({ id: 'steam:2', name: 'Other Game' }),
        ],
      })))
      render(<GamesPage />)
      await screen.findByText('Half-Life 2')
      await user.click(screen.getByRole('button', { name: /show favorites only/i }))
      expect(screen.getByText('Half-Life 2')).toBeInTheDocument()
      expect(screen.queryByText('Other Game')).not.toBeInTheDocument()
    })

    it('shows the favorites empty state when nothing is starred', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
        games: [g({ id: 'steam:9', name: 'Unstarred Game' })],
      })))
      render(<GamesPage />)
      await screen.findByText('Unstarred Game')
      await user.click(screen.getByRole('button', { name: /show favorites only/i }))
      expect(await screen.findByText('No favorites yet — star a game to pin it here')).toBeInTheDocument()
    })
  })

  describe('details panel', () => {
    const sessionData = {
      game: g({}),
      session: {
        running: true,
        started_at: 1700000000,
        duration_s: 3720,
        game_cpu_pct: 23.5,
        game_ram_mb: 4096,
      },
      system_metrics: {
        cpu: 41, ram: 62, ram_used_gb: 10.4, ram_total_gb: 16,
        gpu: 77, gpu_temp: 68, network_download: 1.2, network_upload: 0.4,
      },
      profile: { id: 'cs2', name: 'Counter-Strike 2' },
      now: 1700003720,
    }

    it('opens the details panel with real backend session metrics', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibrarySession).mockReturnValue(ok(sessionData))
      render(<GamesPage />)
      await user.click(await screen.findByRole('button', { name: /open details for half-life 2/i }))
      /* Session metrics from the backend — real values only. */
      expect(await screen.findByText('1h 02m')).toBeInTheDocument()  // 3720s
      expect(screen.getByText('23.5%')).toBeInTheDocument()          // game CPU
      expect(screen.getByText('4096 MB')).toBeInTheDocument()        // game RAM
      expect(screen.getByText('77%')).toBeInTheDocument()            // GPU load
      expect(screen.getByText('68°C')).toBeInTheDocument()           // GPU temp
      expect(screen.getByText('C:/Games/HalfLife2')).toBeInTheDocument() // install path
    })

    it('renders an em dash for unavailable metrics instead of fake 0s', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibrarySession).mockReturnValue(ok({
        ...sessionData,
        session: { running: false, started_at: null, duration_s: null, game_cpu_pct: null, game_ram_mb: null },
        system_metrics: { cpu: null, ram: null, gpu: null, gpu_temp: null, network_download: null, network_upload: null },
      }))
      render(<GamesPage />)
      await user.click(await screen.findByRole('button', { name: /open details for half-life 2/i }))
      expect(await screen.findByText('Session time')).toBeInTheDocument()
      /* Every unavailable value is an em dash, not a fabricated number. */
      const dashes = screen.getAllByText('—')
      expect(dashes.length).toBeGreaterThanOrEqual(8)
      expect(screen.queryByText(/^\d+%$/)).not.toBeInTheDocument()
    })

    it('explains honestly when the session request fails', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibrarySession).mockRejectedValue(new Error('session: 500'))
      render(<GamesPage />)
      await user.click(await screen.findByRole('button', { name: /open details for half-life 2/i }))
      expect(await screen.findByText('Session data unavailable — the Optinix service did not respond.')).toBeInTheDocument()
    })

    it('closes the details panel', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibrarySession).mockReturnValue(ok(sessionData))
      render(<GamesPage />)
      await user.click(await screen.findByRole('button', { name: /open details for half-life 2/i }))
      await screen.findByText('Current session')
      await user.click(screen.getByRole('button', { name: /close details/i }))
      expect(screen.queryByText('Current session')).not.toBeInTheDocument()
    })
  })

  /* ---------------- Gaming Center V2: manual imports & emulators --------- */

  describe('manual imports', () => {
    it('adds an exe via the Add Game panel and refreshes the library', async () => {
      const user = userEvent.setup()
      render(<GamesPage />)
      await screen.findByText('Half-Life 2')
      await user.click(screen.getByRole('button', { name: /add game$/i }))
      await user.type(screen.getByLabelText(/full path to the game's .exe/i), 'C:/Games/X/game.exe')
      await user.type(screen.getByLabelText(/display name/i), 'My Manual Game')
      await user.click(screen.getByRole('button', { name: /add to library/i }))
      await screen.findByText(/added to the library/i)
      expect(api.gameLibraryAddExe).toHaveBeenCalledWith({ exe_path: 'C:/Games/X/game.exe', name: 'My Manual Game', emulator_id: null })
      expect(api.gameLibrary).toHaveBeenCalledTimes(2) // initial + refresh
    })

    it('scans a folder and requires an explicit exe choice — no auto-pick', async () => {
      const user = userEvent.setup()
      render(<GamesPage />)
      await screen.findByText('Half-Life 2')
      await user.click(screen.getByRole('button', { name: /add game$/i }))
      await user.click(screen.getByRole('button', { name: 'From a folder' }))
      await user.type(screen.getByLabelText(/game installation folder/i), 'C:/Games/X')
      await user.click(screen.getByRole('button', { name: /find game executables/i }))
      expect(await screen.findByText(/1 possible game executables found/i)).toBeInTheDocument()
      expect(api.gameLibraryScanFolder).toHaveBeenCalledWith('C:/Games/X')
      /* The candidate list appears for the user to choose — nothing added yet. */
      expect(api.gameLibraryAddFolder).not.toHaveBeenCalled()
      await user.click(screen.getByRole('radio'))
      await user.click(screen.getByRole('button', { name: /add folder game/i }))
      await screen.findByText(/folder game added/i)
      expect(api.gameLibraryAddFolder).toHaveBeenCalledWith({ folder: 'C:/Games/X', exe_path: 'C:/Games/X/GameClient.exe', name: '' })
    })

    it('resolves a shortcut without executing it and shows the target', async () => {
      const user = userEvent.setup()
      render(<GamesPage />)
      await screen.findByText('Half-Life 2')
      await user.click(screen.getByRole('button', { name: /add game$/i }))
      await user.click(screen.getByRole('button', { name: 'Shortcut' }))
      await user.type(screen.getByLabelText(/path to the .lnk shortcut/i), 'C:/Users/x/Desktop/Game.lnk')
      await user.click(screen.getByRole('button', { name: /resolve target/i }))
      expect(await screen.findByText(/safe to import/i)).toBeInTheDocument()
      expect(api.gameLibraryResolveShortcut).toHaveBeenCalledWith('C:/Users/x/Desktop/Game.lnk')
      expect(api.gameLibraryAddExe).not.toHaveBeenCalled() // until user confirms
      await user.click(screen.getByRole('button', { name: /import target/i }))
      await screen.findByText(/imported as a manually added game/i)
      expect(api.gameLibraryAddExe).toHaveBeenCalledWith({ exe_path: 'C:/Games/RealGame.exe', name: '', emulator_id: null })
    })

    it('launches a manual game through the manual-launch endpoint', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
        games: [g({ id: 'manual:m1', name: 'Picked Game', source: 'manual', label: 'manually added' })],
      })))
      render(<GamesPage />)
      await user.click(await screen.findByRole('button', { name: /launch/i }))
      expect(api.gameLibraryManualLaunch).toHaveBeenCalledWith('manual:m1')
      expect(api.gameLibraryLaunch).not.toHaveBeenCalled()
    })
  })

  describe('emulators', () => {
    it('registers an emulator and lists it', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibraryEmulators).mockReturnValue(ok({ emulators: [{ id: 'emu:1', name: 'BlueStacks', exe_path: 'C:/emu/HD-Player.exe', args: '--vm x', added_at: 0 }] }))
      render(<GamesPage />)
      await screen.findByText('Half-Life 2')
      await user.click(screen.getByRole('button', { name: /add game$/i }))
      await user.click(screen.getByRole('button', { name: 'Emulator' }))
      expect(await screen.findByText('BlueStacks')).toBeInTheDocument()
      await user.type(screen.getByLabelText(/emulator name/i), 'MuMu')
      await user.type(screen.getByLabelText(/full path to the emulator's .exe/i), 'C:/emu/MuMuPlayer.exe')
      await user.click(screen.getByRole('button', { name: /register emulator/i }))
      await screen.findByText(/emulator registered/i)
      expect(api.gameLibraryAddEmulator).toHaveBeenCalledWith({ name: 'MuMu', exe_path: 'C:/emu/MuMuPlayer.exe', args: '' })
    })

    it('shows emulator-associated games with the via badge and groups them under the Emulator filter', async () => {
      const user = userEvent.setup()
      vi.mocked(api.gameLibraryEmulators).mockReturnValue(ok({ emulators: [{ id: 'emu:1', name: 'BlueStacks', exe_path: 'C:/emu/HD-Player.exe', args: '', added_at: 0 }] }))
      vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
        games: [
          g({}),
          g({ id: 'manual:e1', name: 'Emu Game', source: 'manual', emulator_id: 'emu:1', emulator: { id: 'emu:1', name: 'BlueStacks', exe_path: 'C:/emu/HD-Player.exe', args: '', added_at: 0 } }),
        ],
      })))
      render(<GamesPage />)
      expect(await screen.findByText('Emu Game')).toBeInTheDocument()
      expect(screen.getByText(/via BlueStacks/i)).toBeInTheDocument()
      expect(screen.getAllByText('Manually added').length).toBeGreaterThan(0)
      await user.selectOptions(screen.getByRole('combobox', { name: /filter by library category/i }), 'emulator')
      expect(screen.getByText('Emu Game')).toBeInTheDocument()
      expect(screen.queryByText('Half-Life 2')).not.toBeInTheDocument()
    })
  })

  describe('artwork fallback', () => {
    it('uses the backend artwork route and swaps to the fallback tile when it fails', async () => {
      vi.mocked(api.gameLibrary).mockReturnValue(ok(makeLibrary({
        games: [g({ appid: 730 })],
      })))
      render(<GamesPage />)
      const img = await screen.findByAltText('')
      expect(img).toBeInTheDocument()
      /* Covers must come from the backend's cache route — never a raw CDN
         URL, which 404s for newer titles and needs the server-side fix. */
      expect(img.getAttribute('src')).toContain('/api/game-library/artwork?id=')
      /* Simulate a 404/no-artwork response — the component must swap to
         the lettered tile rather than leaving a broken image. */
      fireEvent.error(img)
      await screen.findByText('H') // initial tile
      expect(screen.queryByAltText('')).not.toBeInTheDocument()
    })
  })
})

