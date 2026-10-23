import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NetworkPage } from './NetworkPage'
import type {
  SystemInfo,
  NetworkAnalyzeResult,
  NetworkTraceResult,
} from '../../types'

/* Mock the API module: the page must render real measurements, must render an
   honest unavailable state when a probe reports no reply, and must never
   invent a number the backend did not send. */
vi.mock('../../lib/api', () => ({
  api: {
    networkAdapters: vi.fn(),
    dns: vi.fn(),
    flushDns: vi.fn(),
    qos: vi.fn(),
    bufferbloat: vi.fn(),
    advancedNetwork: vi.fn(),
    ping: vi.fn(),
    networkTargets: vi.fn(),
    networkDnsServers: vi.fn(),
    networkAnalyze: vi.fn(),
    networkTrace: vi.fn(),
  },
}))

import { api } from '../../lib/api'

const ok = <T,>(value: T) => Promise.resolve(value)

const mockSystemInfo = (): SystemInfo => ({
  network: { bytes_sent: 1_000_000, bytes_recv: 5_000_000, speed_down: 2_500_000, speed_up: 250_000 },
} as unknown as SystemInfo)

const mockAnalyze = (overrides: Partial<NetworkAnalyzeResult['latency']> = {}): NetworkAnalyzeResult => ({
  target: '1.1.1.1',
  latency: {
    ok: true,
    host: '1.1.1.1',
    avg_ms: 14.2,
    min_ms: 12.1,
    max_ms: 19.8,
    jitter_ms: 2.4,
    packet_loss_pct: 0,
    sent: 10,
    received: 10,
    sub_ms: false,
    samples_ms: [14.1, 13.9, 15.2, 12.1, 19.8],
    ...overrides,
  },
  dns: { ok: true, host: '1.1.1.1', addresses: ['1.1.1.1'], resolve_ms: 3.1 },
  timestamp: 1_700_000_000,
  methodology: {
    jitter: 'Population standard deviation of round-trip times.',
    packet_loss: 'Percentage of sent probes with no reply.',
    routing_note: 'Diagnostics only; Optinix does not reroute traffic.',
  },
})

describe('NetworkPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.networkAdapters).mockReturnValue(ok({ adapters: [] }))
  })

  it('renders real measurement values from the analyze result', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkAnalyze).mockReturnValue(ok(mockAnalyze()))
    render(<NetworkPage systemInfo={mockSystemInfo()} />)

    const measure = await screen.findByRole('button', { name: /Measure/ })
    await user.click(measure)

    await waitFor(() => expect(api.networkAnalyze).toHaveBeenCalledWith('1.1.1.1'))
    const metrics = await screen.findByTestId('intel-metrics')
    expect(metrics).toHaveTextContent('14.2 ms')
    expect(metrics).toHaveTextContent('2.4 ms')
    expect(metrics).toHaveTextContent('0%')
    expect(metrics).toHaveTextContent('10/10 replies')
  })

  it('shows an honest unavailable state when the probe gets no reply', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkAnalyze).mockReturnValue(
      ok(mockAnalyze({
        ok: false,
        avg_ms: null,
        min_ms: null,
        max_ms: null,
        jitter_ms: null,
        packet_loss_pct: null,
        error: 'No replies from 10.255.255.1',
      })),
    )
    render(<NetworkPage systemInfo={mockSystemInfo()} />)

    await user.click(await screen.findByRole('button', { name: /Measure/ }))

    await waitFor(() =>
      expect(screen.getByText(/No replies from 10\.255\.255\.1/)).toBeInTheDocument(),
    )
    /* The container renders, but only the honest banner — never a fabricated
       latency the backend did not send. */
    const metrics = await screen.findByTestId('intel-metrics')
    expect(metrics).toHaveTextContent('No reply from 1.1.1.1')
    expect(screen.queryByText('14.2 ms')).not.toBeInTheDocument()
    expect(screen.queryByText('2.4 ms')).not.toBeInTheDocument()
  })

  it('renders the backend error state when the request fails', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkAnalyze).mockRejectedValue(new Error('fetch failed'))
    render(<NetworkPage systemInfo={mockSystemInfo()} />)

    await user.click(await screen.findByRole('button', { name: /Measure/ }))

    await waitFor(() => expect(screen.getByText('fetch failed')).toBeInTheDocument())
    expect(screen.queryByTestId('intel-metrics')).not.toBeInTheDocument()
  })

  it('renders hop data from the trace result and labels a timed-out hop', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkTrace).mockReturnValue(
      ok({
        ok: true,
        host: '1.1.1.1',
        hops: [
          { ip: '192.168.1.1', ok: true, avg_ms: 1.2, times_ms: [1.1, 1.2, 1.3] },
          { ip: '*', ok: false },
          { ip: '1.1.1.1', ok: true, avg_ms: 14.0, times_ms: [13.9, 14.1, 14.0] },
        ],
      } satisfies NetworkTraceResult),
    )
    render(<NetworkPage systemInfo={mockSystemInfo()} />)

    await user.click(await screen.findByRole('button', { name: /Run trace/ }))

    const trace = await screen.findByTestId('intel-trace')
    await waitFor(() => expect(trace).toHaveTextContent('192.168.1.1'))
    expect(trace).toHaveTextContent('1.1.1.1')
    expect(trace).toHaveTextContent('1.2 ms')
    /* The unreachable hop must be labelled, not silently dropped. */
    expect(trace).toHaveTextContent('Timed out')
  })

  it('renders the trace error state when the trace request fails', async () => {
    const user = userEvent.setup()
    vi.mocked(api.networkTrace).mockRejectedValue(new Error('trace unreachable'))
    render(<NetworkPage systemInfo={mockSystemInfo()} />)

    await user.click(await screen.findByRole('button', { name: /Run trace/ }))

    await waitFor(() => expect(screen.getByText('trace unreachable')).toBeInTheDocument())
    expect(screen.queryByTestId('intel-trace')).not.toBeInTheDocument()
  })
})
