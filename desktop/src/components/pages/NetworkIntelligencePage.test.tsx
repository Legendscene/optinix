import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NetworkIntelligencePage } from './NetworkIntelligencePage'
import type { NetworkAnalyzeResult } from '../../types'

/* The page must render real measurements plus their DNS resolution
   diagnostics, must keep "DNS failed" distinct from "host is down", and must
   never invent a number the backend did not send. */
vi.mock('../../lib/api', () => ({
  api: {
    networkTargets: vi.fn(),
    networkDnsServers: vi.fn(),
    networkAnalyze: vi.fn(),
    networkTrace: vi.fn(),
  },
}))

import { api } from '../../lib/api'

const ok = <T,>(value: T) => Promise.resolve(value)

const mockAnalyze = (overrides: Partial<NetworkAnalyzeResult> = {}): NetworkAnalyzeResult => ({
  target: 'store.steampowered.com',
  latency: {
    ok: true,
    host: 'store.steampowered.com',
    avg_ms: 18.6,
    min_ms: 16.2,
    max_ms: 24.9,
    jitter_ms: 3.1,
    packet_loss_pct: 0,
    sent: 10,
    received: 10,
    samples_ms: [18.2, 17.9, 24.9, 16.2],
  },
  dns: {
    ok: true,
    host: 'store.steampowered.com',
    addresses: ['155.133.248.38', '155.133.248.39'],
    resolve_ms: 12.4,
  },
  timestamp: 1_700_000_000,
  methodology: {
    jitter: 'population standard deviation of round-trip times',
    packet_loss: 'percentage of sent probes with no reply',
    routing_note: 'Diagnostics only.',
  },
  ...overrides,
})

describe('NetworkIntelligencePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.networkTargets).mockReturnValue(ok({
      targets: [{ id: 'steam', label: 'Steam', host: 'store.steampowered.com', note: 'CDN' }],
    }))
    vi.mocked(api.networkDnsServers).mockReturnValue(ok({ ok: true, servers: ['1.1.1.1'] }))
  })

  it('renders real measurements with per-target DNS resolution diagnostics', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkAnalyze).mockReturnValue(ok(mockAnalyze()))
    render(<NetworkIntelligencePage />)

    await user.click(await screen.findByRole('button', { name: /Measure/ }))

    await waitFor(() => expect(api.networkAnalyze).toHaveBeenCalledWith('store.steampowered.com', 10))
    /* The measured average renders as the live metric and again in the
       session-history row the page appends — both are the same real value. */
    expect((await screen.findAllByText('18.6 ms')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('3.1 ms').length).toBeGreaterThan(0)

    /* DNS resolution is a separate measurement from the ICMP probes and must
       show both the resolved addresses and the lookup time. */
    const dns = await screen.findByTestId('dns-diagnostics')
    expect(dns).toHaveTextContent('store.steampowered.com')
    expect(dns).toHaveTextContent('155.133.248.38, 155.133.248.39')
    expect(dns).toHaveTextContent('12.4 ms')
  })

  it('keeps a DNS failure distinct from a dead host', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkAnalyze).mockReturnValue(ok(mockAnalyze({
      dns: { ok: false, host: 'store.steampowered.com', resolve_ms: 3000, error: 'Could not resolve store.steampowered.com: Name or service not known' },
    })))
    render(<NetworkIntelligencePage />)

    await user.click(await screen.findByRole('button', { name: /Measure/ }))

    const dns = await screen.findByTestId('dns-diagnostics')
    expect(dns).toHaveTextContent('Could not resolve store.steampowered.com')
    /* The distinction the diagnostic exists to make: ICMP to an IP can work
       even when DNS is broken. */
    expect(dns).toHaveTextContent(/ICMP probes to an IP address can still succeed/)
    /* Latency was still measured fine and must still render. */
    expect(screen.getAllByText('18.6 ms').length).toBeGreaterThan(0)
  })

  it('shows the honest no-reply state without fabricating latency', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkAnalyze).mockReturnValue(ok(mockAnalyze({
      latency: { ok: false, host: 'store.steampowered.com', error: 'No replies from 10.255.255.1' },
    })))
    render(<NetworkIntelligencePage />)

    await user.click(await screen.findByRole('button', { name: /Measure/ }))

    await waitFor(() => expect(screen.getByText(/No replies from 10\.255\.255\.1/)).toBeInTheDocument())
    expect(screen.queryByText('18.6 ms')).not.toBeInTheDocument()
    expect(screen.queryByText('0 ms')).not.toBeInTheDocument()
  })

  it('renders the backend error naming the host that failed', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkAnalyze).mockRejectedValue(new Error('/api/network/analyze: 400'))
    render(<NetworkIntelligencePage />)

    await user.click(await screen.findByRole('button', { name: /Measure/ }))

    await waitFor(() => expect(screen.getByText('/api/network/analyze: 400')).toBeInTheDocument())
    expect(screen.getByText(/Could not measure/)).toHaveTextContent('store.steampowered.com')
  })

  it('carries the diagnostics-only disclaimer (no routing claims)', () => {
    render(<NetworkIntelligencePage />)
    expect(screen.getByText(/Diagnostics only/)).toBeInTheDocument()
    expect(screen.getByText(/does not reroute your traffic/)).toBeInTheDocument()
    /* The disclaimer names multipath/optimized routes only to state they are
       not offered — the claim must be a denial, never an offer. */
    expect(screen.getByText(/not offered/)).toBeInTheDocument()
  })
})
