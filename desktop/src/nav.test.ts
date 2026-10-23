import { describe, it, expect } from 'vitest'
import {
  ZONES, TOOLS, TOOL_MAP, ZONE_MAP, LEGACY_ROUTES,
  searchTools, toolsInZone,
} from './nav'

const ZONE_IDS = new Set<string>(ZONES.map((z) => z.id))

describe('information architecture', () => {
  it('defines exactly 12 destinations', () => {
    expect(ZONES).toHaveLength(12)
  })

  it('every tool belongs to a real destination', () => {
    for (const t of TOOLS) {
      expect(ZONE_MAP[t.zone], `${t.id} -> ${t.zone}`).toBeDefined()
    }
  })

  it('no tool id collides with a destination id', () => {
    for (const t of TOOLS) {
      expect(ZONE_IDS.has(t.id), `${t.id} collides with a destination`).toBe(false)
    }
  })

  it('tool ids are unique', () => {
    const ids = TOOLS.map((t) => t.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('every legacy route resolves to a real destination', () => {
    for (const [from, to] of Object.entries(LEGACY_ROUTES)) {
      expect(ZONE_IDS.has(to), `${from} -> ${to}`).toBe(true)
    }
  })

  it('each destination has at least one tool or a direct page', () => {
    /* These destinations render dedicated pages in App.tsx instead of a tool
       hub, so a tool-less destination is only acceptable for them. */
    const direct = new Set(['home', 'games', 'personalization', 'reports'])
    for (const z of ZONES) {
      const hasTools = TOOLS.some((t) => t.zone === z.id)
      expect(hasTools || direct.has(z.id), `${z.id} is empty`).toBe(true)
    }
  })

  it('every destination hub groups its tools without loss', () => {
    for (const z of ZONES) {
      const inZone = toolsInZone(z.id)
      expect(inZone.filter((t) => t.zone === z.id)).toHaveLength(inZone.length)
    }
  })
})

describe('palette search reachability', () => {
  it('finds every tool by its own label', () => {
    for (const t of TOOLS) {
      const hits = searchTools(t.label.toLowerCase())
      expect(hits.map((h) => h.id), `search "${t.label}"`).toContain(t.id)
    }
  })

  it('finds tools by common keyword shortcuts', () => {
    const cases: Record<string, string> = {
      ram: 'memory',
      junk: 'cleanup',
      dns: 'internet',
      fps: 'game-tweaks',
      ping: 'speed-test',
      undo: 'rollback',
    }
    for (const [query, expected] of Object.entries(cases)) {
      const hits = searchTools(query).map((h) => h.id)
      expect(hits, `search "${query}"`).toContain(expected)
    }
  })

  it('is empty for blank queries', () => {
    expect(searchTools('')).toEqual([])
    expect(searchTools('   ')).toEqual([])
  })

  it('excludes non-matches', () => {
    const hits = searchTools('zzzzqqqq').map((h) => h.id)
    expect(hits).toHaveLength(0)
  })
})

describe('tool registry integrity', () => {
  it('TOOL_MAP mirrors TOOLS', () => {
    expect(Object.keys(TOOL_MAP)).toHaveLength(TOOLS.length)
    for (const t of TOOLS) expect(TOOL_MAP[t.id]).toBe(t)
  })

  it('legacy favourites from the old shell are filtered, not crashing', () => {
    /* Old ids that no longer exist (renamed) must not resolve. */
    for (const gone of ['gaming', 'network', 'diagnostics', 'settings', 'home']) {
      if (ZONE_IDS.has(gone)) continue // still valid as a destination
      expect(TOOL_MAP[gone]).toBeUndefined()
    }
  })
})
