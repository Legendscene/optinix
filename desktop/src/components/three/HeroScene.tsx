import { useMemo, useRef, useState, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

/**
 * The single 3D experience in the app: a floating geometric Optinix emblem.
 * One scene, one chunk, no post-processing chain — quality comes from
 * materials, three coloured lights and depth cues, not from effects that
 * cost frames.
 *
 * Composition, outside in:
 *  - a slow dust field (additive points) that gives the object real depth
 *  - two tilted rings with satellites riding them at different speeds
 *  - a wireframe shell over a faceted emissive core
 * The emblem builds in over ~0.9s on mount, then idles on that motion.
 *
 * Performance contract:
 *  - `frameloop` flips to "never" while the tab is hidden or the user
 *    asked for reduced motion: zero GPU/CPU work, last frame preserved.
 *  - `dpr` is clamped to [1, 1.75] so hi-DPI screens don't render 4x
 *    pixels for a 300px widget.
 *  - `powerPreference: 'low-power'` keeps it off the discrete GPU when
 *    the OS would otherwise spin one up for a decorative canvas.
 *  - Geometry is created once (useMemo) and disposed on unmount.
 *  - No animated numbers anywhere: the emblem is atmosphere, not data.
 */

export interface HeroSceneProps {
  /** False while the document is hidden or the user prefers reduced motion. */
  active: boolean
  /**
   * Live load, 0..1, from the page's own readings. It only scales how hard the
   * emblem burns and how fast it orbits, so the scene reflects the machine
   * without ever encoding numbers into the picture. Clamped, defaulted, and
   * read inside the frame loop only — a new value never re-creates materials.
   */
  level?: number
  /** Called if the WebGL context is lost; wrapper swaps to the fallback. */
  onContextLost?: () => void
}

interface OrbitSpec {
  radius: number
  speed: number
  tilt: [number, number, number]
  color: string
  size: number
  phase: number
}

const ORBITS: OrbitSpec[] = [
  { radius: 1.78, speed: 0.5, tilt: [Math.PI / 2.4, 0.2, 0], color: '#8b7bf7', size: 0.085, phase: 0 },
  { radius: 2.02, speed: -0.34, tilt: [Math.PI / 3.1, -0.45, 0.55], color: '#2ff0da', size: 0.06, phase: 2.1 },
  { radius: 1.58, speed: 0.72, tilt: [Math.PI / 1.9, 0.9, -0.35], color: '#5fd6ff', size: 0.045, phase: 4.2 },
]

function Dust({ active, level }: { active: boolean; level: number }) {
  const group = useRef<THREE.Group>(null)

  const { geometry, material } = useMemo(() => {
    const count = 280
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i += 1) {
      /* Shell, not a cube: uniform direction, random radius. */
      const u = Math.random() * 2 - 1
      const theta = Math.random() * Math.PI * 2
      const r = 2.1 + Math.random() * 2.6
      const s = Math.sqrt(1 - u * u)
      positions[i * 3] = Math.cos(theta) * s * r
      positions[i * 3 + 1] = u * r * 0.7
      positions[i * 3 + 2] = Math.sin(theta) * s * r
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const mat = new THREE.PointsMaterial({
      size: 0.032,
      color: '#9df7ec',
      transparent: true,
      opacity: 0.5,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    })
    return { geometry: geo, material: mat }
  }, [])

  useEffect(() => () => { geometry.dispose(); material.dispose() }, [geometry, material])

  useFrame((_, delta) => {
    if (!active || !group.current) return
    const d = Math.min(delta, 0.05)
    group.current.rotation.y += d * (0.03 + level * 0.05)
    group.current.rotation.x = Math.sin(performance.now() * 0.00012) * 0.05
  })

  return (
    <points ref={group} geometry={geometry} material={material} />
  )
}

function Orbit({ spec, geometry, active, level }: {
  spec: OrbitSpec
  geometry: THREE.BufferGeometry
  active: boolean
  level: number
}) {
  const spin = useRef<THREE.Group>(null)
  const mat = useRef<THREE.MeshBasicMaterial>(null)

  const lean = useMemo(() => new THREE.MeshBasicMaterial({
    color: spec.color, transparent: true, opacity: 0.45,
  }), [spec.color])
  useEffect(() => () => { lean.dispose() }, [lean])

  useFrame(({ clock }, delta) => {
    if (!active || !spin.current) return
    /* Load raises orbital speed: a busy machine visibly spins faster. */
    spin.current.rotation.y += Math.min(delta, 0.05) * spec.speed * (0.55 + level * 1.1)
    if (mat.current) {
      /* Slow breathe: the satellites read as traffic, not decoration. */
      mat.current.opacity = 0.62 + level * 0.18 + Math.sin(clock.elapsedTime * 1.6 + spec.phase) * 0.2
    }
  })

  return (
    <group rotation={spec.tilt}>
      <group ref={spin} rotation={[0, spec.phase, 0]}>
        <mesh position={[spec.radius, 0, 0]} geometry={geometry} scale={spec.size * 9}>
          <meshBasicMaterial ref={mat} color={spec.color} transparent opacity={0.9} />
        </mesh>
        {/* A second satellite 180 degrees round keeps the orbit visibly alive. */}
        <mesh position={[-spec.radius, 0, 0]} geometry={geometry} scale={spec.size * 5} material={lean} />
      </group>
    </group>
  )
}

function Emblem({ active, level }: { active: boolean; level: number }) {
  const group = useRef<THREE.Group>(null)
  const born = useRef<number | null>(null)
  const { pointer } = useThree()

  /* Geometry/materials shared by the core and its wireframe shell. */
  const [coreGeo, shellGeo, ringGeo, satGeo] = useMemo(() => [
    new THREE.IcosahedronGeometry(1.05, 0),
    new THREE.IcosahedronGeometry(1.07, 0),
    new THREE.TorusGeometry(1.78, 0.011, 8, 120),
    new THREE.OctahedronGeometry(0.1, 0),
  ], [])

  const coreMat = useMemo(() => new THREE.MeshStandardMaterial({
    color: '#1a2430',
    /* Low metalness on purpose: a metal without an environment map
       renders black. The colour comes from the lights + emissive. */
    metalness: 0.2,
    roughness: 0.38,
    flatShading: true,
    emissive: new THREE.Color('#0f8f80'),
    emissiveIntensity: 0.62,
  }), [])

  const shellMat = useMemo(() => new THREE.MeshBasicMaterial({
    color: '#2ff0da',
    wireframe: true,
    transparent: true,
    opacity: 0.6,
  }), [])

  const ringMatA = useMemo(() => new THREE.MeshBasicMaterial({
    color: '#00e5cc', transparent: true, opacity: 0.62,
  }), [])
  const ringMatB = useMemo(() => new THREE.MeshBasicMaterial({
    color: '#8b7bf7', transparent: true, opacity: 0.42,
  }), [])
  const ringMatC = useMemo(() => new THREE.MeshBasicMaterial({
    color: '#2ff0da', transparent: true, opacity: 0.22,
  }), [])

  /* One home for every disposable — R3F disposes what it creates, but
     these are made by hand, so we release them by hand too. */
  useEffect(() => () => {
    coreGeo.dispose(); shellGeo.dispose(); ringGeo.dispose(); satGeo.dispose()
    coreMat.dispose(); shellMat.dispose(); ringMatA.dispose(); ringMatB.dispose(); ringMatC.dispose()
  }, [coreGeo, shellGeo, ringGeo, satGeo, coreMat, shellMat, ringMatA, ringMatB, ringMatC])

  useFrame((state, delta) => {
    if (!group.current) return
    const d = Math.min(delta, 0.05)

    /* Build-in: scale and a touch of lift settle in under a second. Runs
       once; with reduced motion the target is applied immediately. */
    if (born.current == null) born.current = state.clock.elapsedTime
    const age = state.clock.elapsedTime - born.current
    const k = active ? Math.min(1, age / 0.9) : 1
    const eased = 1 - (1 - k) ** 3
    group.current.scale.setScalar(0.88 + 0.12 * eased)

    if (!active) return

    group.current.rotation.y += d * (0.14 + level * 0.16)
    /* Subtle pointer parallax: eased toward the pointer, never snapping.
       Magnitude is small so the emblem stays a backdrop. */
    const tx = pointer.y * 0.18
    const tz = pointer.x * 0.12
    group.current.rotation.x += (tx - group.current.rotation.x) * 0.04
    group.current.rotation.z += (tz - group.current.rotation.z) * 0.04

    /* The core burns harder as the machine works. Eased so a jump in load
       reads as a surge, not a flicker. */
    const target = 0.42 + level * 0.85
    coreMat.emissiveIntensity += (target - coreMat.emissiveIntensity) * 0.06
  })

  return (
    <group ref={group}>
      <Dust active={active} level={level} />

      <mesh geometry={coreGeo} material={coreMat} />
      <mesh geometry={shellGeo} material={shellMat} scale={1.045} />

      {/* Ring scaffolding */}
      <mesh geometry={ringGeo} material={ringMatA} rotation={[Math.PI / 2.4, 0.2, 0]} />
      <mesh geometry={ringGeo} material={ringMatB} rotation={[Math.PI / 3.2, -0.5, 0.6]} scale={1.14} />

      {ORBITS.map((spec) => (
        <Orbit key={spec.color + spec.radius} spec={spec} geometry={satGeo} active={active} level={level} />
      ))}
    </group>
  )
}

/** With frameloop="never" R3F draws nothing — not even the first frame.
 *  If the page mounts while hidden (or the user prefers reduced motion),
 *  the canvas would stay blank forever. Invalidate once after mount so a
 *  single static frame is drawn and preserved. */
function FirstFrame({ active }: { active: boolean }) {
  const invalidate = useThree((s) => s.invalidate)
  /* Re-draw whenever the loop state flips so a paused mount still ends up
     with a rendered frame on screen. */
  useEffect(() => { invalidate() }, [invalidate, active])
  return null
}

function Lights() {
  /* Two coloured keys + one soft fill. Cheap: three lights, no shadows
     (castShadow is off — a decorative emblem has nothing to shadow onto). */
  return (
    <>
      <ambientLight intensity={0.85} />
      <pointLight position={[3.5, 2.5, 4]} intensity={42} color="#7ff5e6" distance={22} decay={2} />
      <pointLight position={[-3.5, -1.5, -2]} intensity={28} color="#8b7bf7" distance={22} decay={2} />
      <directionalLight position={[0, 4, 2]} intensity={1.05} color="#ffffff" />
    </>
  )
}

export default function HeroScene({ active, level = 0.45, onContextLost }: HeroSceneProps) {
  /* Clamp once per render; the frame loop reads the number, never state. */
  const energy = Number.isFinite(level) ? Math.min(1, Math.max(0, level)) : 0.45
  const [paused, setPaused] = useState(() => document.hidden)

  /* Pause without prop-drilling: watch visibility right here so the
     canvas stops rendering the moment the window is backgrounded.

     A page can mount *while already hidden* (app boot, reload in a
     background window); the event listener alone would then never fire
     and the loop would stay parked forever. A 2s re-check runs only
     while paused, so the visible state costs nothing. */
  useEffect(() => {
    const onVis = () => setPaused(document.hidden)
    document.addEventListener('visibilitychange', onVis)
    let poll: ReturnType<typeof setInterval> | undefined
    if (document.hidden) {
      poll = setInterval(() => {
        if (!document.hidden) {
          setPaused(false)
          if (poll) clearInterval(poll)
        }
      }, 2000)
    }
    return () => {
      document.removeEventListener('visibilitychange', onVis)
      if (poll) clearInterval(poll)
    }
  }, [])

  const running = active && !paused

  return (
    <Canvas
      /* 'demand' instead of 'never' when parked: idle costs zero frames,
         but any R3F-internal invalidation (resize, prop change) still
         repaints — 'never' can strand a blank canvas after a reload. */
      frameloop={running ? 'always' : 'demand'}
      dpr={[1, 1.75]}
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: 'low-power',
        preserveDrawingBuffer: false,
      }}
      camera={{ position: [0, 0, 5.2], fov: 42 }}
      onCreated={({ gl }) => {
        gl.domElement.addEventListener('webglcontextlost', (e: Event) => {
          e.preventDefault()
          onContextLost?.()
        })
        gl.setClearColor(0x000000, 0)
      }}
      style={{ pointerEvents: 'none' }}
      aria-hidden
    >
      <Lights />
      <FirstFrame active={running} />
      <Emblem active={running} level={energy} />
    </Canvas>
  )
}
