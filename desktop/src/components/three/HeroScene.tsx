import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'

/**
 * The signature 3D experience: a stylised PC tower, built procedurally.
 *
 * Everything that made the old emblem read as decoration is gone — no
 * icosahedron, no orbit wires. This is a physical object: a machined
 * aluminium frame, tempered glass, a lit interior with an intake fan, a
 * graphics card, a cooler and a PSU shroud. The depth cues are real
 * — image-based lighting from a room probe, metal/roughness materials, a
 * contact glow on the floor and a camera that leans with the pointer.
 *
 * Composition is fixed, so the object never depends on an asset that could
 * fail to load, and there is one canvas for the whole app.
 *
 * Performance contract (unchanged from the previous scene):
 *  - `frameloop` flips to "demand" while the tab is hidden or the user asked
 *    for reduced motion: zero GPU/CPU work, last frame preserved.
 *  - `dpr` is clamped to [1, 1.6]; a 300px widget never renders 4x pixels.
 *  - `powerPreference: 'low-power'` keeps it off the discrete GPU.
 *  - Geometry/materials are created once and disposed on unmount; the PMREM
 *    environment is released with them.
 *  - No shadows, no post-processing, one ~1k-triangle assembly.
 *
 * Live load only changes how hard the interior burns and how fast the fan
 * turns — it never encodes data into the picture.
 */

export interface HeroSceneProps {
  /** False while the document is hidden or the user prefers reduced motion. */
  active: boolean
  /** Live load, 0..1, from the page's own readings. */
  level?: number
  /** Called if the WebGL context is lost; wrapper swaps to the fallback. */
  onContextLost?: () => void
}

/** Window-space pointer, normalised to -0.5..0.5 on both axes. Written by one
 * passive listener and read inside the frame loop, so a mouse move never
 * re-renders React. The canvas has pointer-events: none, so R3F's own pointer
 * would never update. */
function useWindowPointer() {
  const pointer = useRef({ x: 0, y: 0 })
  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      pointer.current.x = e.clientX / window.innerWidth - 0.5
      pointer.current.y = e.clientY / window.innerHeight - 0.5
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => window.removeEventListener('pointermove', onMove)
  }, [])
  return pointer
}

/** Image-based lighting. Without an environment map, metal materials render
 * black; a room probe is two dozen lines of setup and makes the aluminium and
 * glass read as real surfaces. */
function Studio() {
  const gl = useThree((s) => s.gl)
  const scene = useThree((s) => s.scene)

  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl)
    const room = new RoomEnvironment()
    const env = pmrem.fromScene(room, 0.04).texture
    scene.environment = env
    scene.environmentIntensity = 0.3
    room.dispose?.()
    pmrem.dispose()
    return () => {
      scene.environment = null
      env.dispose()
      pmrem.dispose()
    }
  }, [gl, scene])

  return null
}

function ContactGlow() {
  const tex = useMemo(() => {
    const c = document.createElement('canvas')
    c.width = c.height = 256
    const ctx = c.getContext('2d')
    if (!ctx) return null
    const g = ctx.createRadialGradient(128, 128, 0, 128, 128, 126)
    g.addColorStop(0, 'rgba(46,230,207,0.55)')
    g.addColorStop(0.45, 'rgba(46,230,207,0.18)')
    g.addColorStop(1, 'rgba(46,230,207,0)')
    ctx.fillStyle = g
    ctx.fillRect(0, 0, 256, 256)
    const t = new THREE.CanvasTexture(c)
    t.colorSpace = THREE.SRGBColorSpace
    return t
  }, [])

  useEffect(() => () => { tex?.dispose() }, [tex])

  if (!tex) return null
  return (
    <mesh position={[0, -2.05, 0.2]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[5.2, 3.6]} />
      <meshBasicMaterial map={tex} transparent depthWrite={false} blending={THREE.AdditiveBlending} opacity={0.85} />
    </mesh>
  )
}

const CYAN = '#4ff5e0'
const VIOLET = '#a98cff'

/** One intake fan: a machined ring, five blades turning on the face. */
function Fan({
  position, radius, speed, tint, active, level,
}: {
  position: [number, number, number]
  radius: number
  speed: number
  tint: string
  active: boolean
  level: number
}) {
  const rotor = useRef<THREE.Group>(null)
  const glow = useRef<THREE.MeshBasicMaterial>(null)

  const ringGeo = useMemo(() => new THREE.TorusGeometry(radius, 0.016, 8, 56), [radius])
  const hubGeo = useMemo(() => new THREE.CylinderGeometry(radius * 0.19, radius * 0.19, 0.05, 20), [radius])
  const bladeGeo = useMemo(() => new THREE.BoxGeometry(radius * 0.7, radius * 0.15, 0.015), [radius])
  const backGeo = useMemo(() => new THREE.CircleGeometry(radius * 0.97, 40), [radius])

  const ringMat = useMemo(
    () => new THREE.MeshStandardMaterial({ color: '#333c48', metalness: 0.95, roughness: 0.24 }),
    [],
  )
  const hubMat = useMemo(
    () => new THREE.MeshStandardMaterial({ color: '#1b2029', metalness: 0.85, roughness: 0.35 }),
    [],
  )
  const bladeMat = useMemo(
    () => new THREE.MeshStandardMaterial({ color: '#0b0f14', metalness: 0.4, roughness: 0.6 }),
    [],
  )
  const backMat = useMemo(
    () => new THREE.MeshBasicMaterial({ color: '#05080b' }),
    [],
  )
  const glowMat = useMemo(
    () => new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0.9 }),
    [tint],
  )

  useEffect(() => () => {
    ringGeo.dispose(); hubGeo.dispose(); bladeGeo.dispose(); backGeo.dispose()
    ringMat.dispose(); hubMat.dispose(); bladeMat.dispose(); glowMat.dispose(); backMat.dispose()
  }, [ringGeo, hubGeo, bladeGeo, backGeo, ringMat, hubMat, bladeMat, glowMat, backMat])

  useFrame((_, delta) => {
    if (!active || !rotor.current) return
    rotor.current.rotation.z -= Math.min(delta, 0.05) * speed * (0.55 + level * 2.2)
    if (glow.current) glow.current.opacity = 0.55 + level * 0.4
  })

  return (
    <group position={position}>
      {/* Dark rotor plate: the fan sits in a housing, not in mid-air. */}
      <mesh geometry={backGeo} material={backMat} position={[0, 0, -0.02]} />
      <mesh geometry={ringGeo} material={ringMat} />
      <mesh geometry={hubGeo} material={hubMat} rotation={[Math.PI / 2, 0, 0]} />
      <group ref={rotor}>
        {Array.from({ length: 7 }).map((_, i) => (
          <mesh
            key={i}
            geometry={bladeGeo}
            material={bladeMat}
            position={[
              Math.cos((i / 7) * Math.PI * 2) * radius * 0.5,
              Math.sin((i / 7) * Math.PI * 2) * radius * 0.5,
              0.008,
            ]}
            rotation={[0, 0, (i / 7) * Math.PI * 2 + 0.45]}
          />
        ))}
      </group>
      <mesh position={[0, 0, 0.02]}>
        <ringGeometry args={[radius * 0.985, radius * 1.02, 56]} />
        <primitive object={glowMat} ref={glow} attach="material" />
      </mesh>
    </group>
  )
}

function Tower({ active, level }: { active: boolean; level: number }) {
  const rig = useRef<THREE.Group>(null)
  const power = useRef<THREE.PointLight>(null)
  const born = useRef<number | null>(null)
  const pointer = useWindowPointer()

  /* Shared geometries — rounded boxes give every plate a machined bevel. */
  const geo = useMemo(() => ({
    side: new RoundedBoxGeometry(0.09, 2.4, 1.7, 4, 0.03),
    top: new RoundedBoxGeometry(1.5, 0.09, 1.7, 4, 0.03),
    back: new RoundedBoxGeometry(1.4, 2.24, 0.05, 3, 0.02),
    glass: new RoundedBoxGeometry(1.4, 2.24, 0.015, 2, 0.008),
    sideGlass: new RoundedBoxGeometry(0.015, 2.24, 1.64, 2, 0.008),
    board: new THREE.BoxGeometry(1.24, 1.96, 0.03),
    gpu: new RoundedBoxGeometry(1.14, 0.15, 0.46, 3, 0.02),
    gpuShroud: new RoundedBoxGeometry(1.18, 0.04, 0.5, 2, 0.012),
    shroud: new RoundedBoxGeometry(1.3, 0.3, 1.1, 3, 0.03),
    cooler: new THREE.CylinderGeometry(0.2, 0.2, 0.12, 24),
    ram: new THREE.BoxGeometry(0.045, 0.46, 0.16),
    strip: new THREE.BoxGeometry(0.018, 1.7, 0.018),
    glowStrip: new THREE.BoxGeometry(0.98, 0.012, 0.012),
  }), [])

  const mat = useMemo(() => ({
    metal: new THREE.MeshStandardMaterial({ color: '#171c24', metalness: 0.95, roughness: 0.3 }),
    glass: new THREE.MeshPhysicalMaterial({
      color: '#cffff8',
      metalness: 0,
      roughness: 0.04,
      transparent: true,
      opacity: 0.09,
      envMapIntensity: 1.2,
      clearcoat: 1,
      clearcoatRoughness: 0.04,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
    board: new THREE.MeshStandardMaterial({ color: '#06100f', metalness: 0.35, roughness: 0.78 }),
    gpu: new THREE.MeshStandardMaterial({ color: '#0d1218', metalness: 0.8, roughness: 0.36 }),
    shroud: new THREE.MeshStandardMaterial({ color: '#12171e', metalness: 0.85, roughness: 0.42 }),
    cooler: new THREE.MeshStandardMaterial({ color: '#20262f', metalness: 0.92, roughness: 0.26 }),
    ram: new THREE.MeshStandardMaterial({ color: '#101820', metalness: 0.6, roughness: 0.45 }),
    accent: new THREE.MeshBasicMaterial({ color: CYAN }),
    violet: new THREE.MeshBasicMaterial({ color: VIOLET }),
  }), [])

  useEffect(() => () => {
    Object.values(geo).forEach((g) => g.dispose())
    Object.values(mat).forEach((m) => m.dispose())
  }, [geo, mat])

  useFrame((state, delta) => {
    if (!rig.current) return
    const d = Math.min(delta, 0.05)
    const t = state.clock.elapsedTime

    /* Build-in once: the tower settles into frame instead of popping. */
    if (born.current == null) born.current = t
    const age = t - born.current
    const k = active ? Math.min(1, age / 1.1) : 1
    const eased = 1 - (1 - k) ** 3
    rig.current.scale.setScalar(0.9 + 0.1 * eased)
    rig.current.position.y = (1 - eased) * -0.35 + Math.sin(t * 0.7) * 0.035

    if (!active) return

    /* Pointer parallax: the case leans a few degrees toward the cursor.
       Eased hard so it never reads as shaking. */
    const targetY = -0.4 + pointer.current.x * 0.28 + Math.sin(t * 0.16) * 0.04
    const targetX = 0.04 - pointer.current.y * 0.13
    rig.current.rotation.y += (targetY - rig.current.rotation.y) * (d * 6)
    rig.current.rotation.x += (targetX - rig.current.rotation.x) * (d * 6)

    if (power.current) {
      power.current.intensity = 6 + level * 16 + Math.sin(t * 1.3) * 1.4
    }
  })

  return (
    <group ref={rig} rotation={[0.04, -0.4, 0]} position={[0, 0, 0]}>
      {/* Frame */}
      <mesh geometry={geo.side} material={mat.metal} position={[-0.7, 0, 0]} />
      <mesh geometry={geo.side} material={mat.metal} position={[0.7, 0, 0]} />
      <mesh geometry={geo.top} material={mat.metal} position={[0, 1.15, 0]} />
      <mesh geometry={geo.top} material={mat.metal} position={[0, -1.15, 0]} />
      <mesh geometry={geo.back} material={mat.metal} position={[0, 0, -0.82]} />

      {/* Interior: board, graphics card, cooler, memory, PSU cover. The
          parts are what make it read as a PC rather than a lit box. */}
      <mesh geometry={geo.board} material={mat.board} position={[0.08, 0.02, -0.66]} />
      {/* Graphics card: the long lit slab across the middle of the build. */}
      <mesh geometry={geo.gpu} material={mat.gpu} position={[0.12, -0.02, 0.1]} rotation={[0, 0, -0.03]} />
      <mesh geometry={geo.gpuShroud} material={mat.metal} position={[0.12, 0.06, 0.1]} rotation={[0, 0, -0.03]} />
      <mesh geometry={geo.glowStrip} material={mat.accent} position={[0.12, 0.085, 0.33]} />
      {/* CPU block with its own lit ring. */}
      <mesh geometry={geo.cooler} material={mat.cooler} position={[0.16, 0.6, -0.05]} rotation={[Math.PI / 2, 0, 0]} />
      <mesh position={[0.16, 0.6, 0.02]}> 
        <ringGeometry args={[0.13, 0.155, 32]} />
        <meshBasicMaterial color={CYAN} transparent opacity={0.85} />
      </mesh>
      <mesh geometry={geo.ram} material={mat.ram} position={[0.48, 0.58, -0.4]} />
      <mesh geometry={geo.ram} material={mat.ram} position={[0.56, 0.58, -0.4]} />
      <mesh geometry={geo.shroud} material={mat.shroud} position={[0.06, -0.92, 0.06]} />

      {/* Cable channel: a vertical plate that hides the PSU bay. */}
      <mesh geometry={geo.ram} material={mat.metal} position={[-0.42, -0.1, -0.35]} scale={[2.6, 2.4, 2.4]} />

      {/* One cyan strip inside the case: the light that reveals the parts. */}
      <mesh geometry={geo.strip} material={mat.accent} position={[-0.63, 0.15, 0.72]} />
      <pointLight ref={power} position={[0.05, 0.25, 0.6]} color={CYAN} intensity={9} distance={3.2} decay={2} />
      <pointLight position={[0.2, -0.7, 0.5]} color={VIOLET} intensity={6} distance={2.4} decay={2} />

      {/* Intake fans on the front edge of the window. */}
      <Fan position={[-0.4, 0.62, 0.5]} radius={0.23} speed={1.35} tint={CYAN} active={active} level={level} />
      <Fan position={[-0.4, -0.52, 0.5]} radius={0.23} speed={1.05} tint={VIOLET} active={active} level={level} />

      {/* Tempered glass: front and side, edge-lit by one hairline. */}
      <mesh geometry={geo.glass} material={mat.glass} position={[0, 0, 0.86]} />
      <mesh geometry={geo.sideGlass} material={mat.glass} position={[0.7, 0, 0]} />
      <mesh position={[0, 1.12, 0.875]}>
        <boxGeometry args={[1.36, 0.012, 0.012]} />
        <primitive object={mat.accent} attach="material" />
      </mesh>
    </group>
  )
}

function Lights() {
  return (
    <>
      <ambientLight intensity={0.16} />
      {/* Key: hard rim light from upper right, the product-photo look. */}
      <spotLight
        position={[3.6, 4.2, 4]}
        angle={0.55}
        penumbra={1}
        intensity={120}
        distance={18}
        color="#d8fffa"
      />
      {/* Cyan bounce from behind, violet from below right: colour on the
          edges only, so the object separates from the room. */}
      <pointLight position={[-2.8, 1.6, -2]} intensity={70} color={CYAN} distance={14} decay={2} />
      <pointLight position={[2.4, -1.6, 1.8]} intensity={26} color={VIOLET} distance={12} decay={2} />
      <pointLight position={[-3, 0.4, 2.6]} intensity={18} color="#6f93ff" distance={14} decay={2} />
      <directionalLight position={[0, 1, 4]} intensity={0.35} color="#ffffff" />
    </>
  )
}

function Dust({ active }: { active: boolean }) {
  const group = useRef<THREE.Group>(null)

  const { geometry, material } = useMemo(() => {
    const count = 110
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i += 1) {
      const u = Math.random() * 2 - 1
      const theta = Math.random() * Math.PI * 2
      const r = 2.0 + Math.random() * 2.4
      const s = Math.sqrt(1 - u * u)
      positions[i * 3] = Math.cos(theta) * s * r
      positions[i * 3 + 1] = u * r * 0.8
      positions[i * 3 + 2] = Math.sin(theta) * s * r
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const mat = new THREE.PointsMaterial({
      size: 0.026,
      color: '#bffcf2',
      transparent: true,
      opacity: 0.35,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    })
    return { geometry: geo, material: mat }
  }, [])

  useEffect(() => () => { geometry.dispose(); material.dispose() }, [geometry, material])

  useFrame((_, delta) => {
    if (!active || !group.current) return
    group.current.rotation.y += Math.min(delta, 0.05) * 0.03
  })

  return <points ref={group} geometry={geometry} material={material} />
}

/** With frameloop="demand" R3F draws nothing — not even the first frame.
 *  If the page mounts while hidden (or the user prefers reduced motion), the
 *  canvas would stay blank forever. Invalidate once after mount so a single
 *  static frame is drawn and preserved. */
function FirstFrame({ active }: { active: boolean }) {
  const invalidate = useThree((s) => s.invalidate)
  useEffect(() => { invalidate() }, [invalidate, active])
  return null
}

export default function HeroScene({ active, level = 0.45, onContextLost }: HeroSceneProps) {
  /* Clamp once per render; the frame loop reads the number, never state. */
  const energy = Number.isFinite(level) ? Math.min(1, Math.max(0, level)) : 0.45
  const [paused] = useHiddenState()

  const running = active && !paused

  return (
    <Canvas
      /* 'demand' instead of 'never' when parked: idle costs zero frames, but
         R3F-internal invalidations (resize) still repaint — 'never' can strand
         a blank canvas after a reload. */
      frameloop={running ? 'always' : 'demand'}
      dpr={[1, 1.6]}
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: 'low-power',
        preserveDrawingBuffer: false,
      }}
      camera={{ position: [0.3, 0.25, 6.3], fov: 34 }}
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
      <Studio />
      <Lights />
      <FirstFrame active={running} />
      <ContactGlow />
      <Dust active={running} />
      <Tower active={running} level={energy} />
    </Canvas>
  )
}

/** Document visibility as state. A page can mount while already hidden (boot
 * in a background window); the event alone would never fire, so a 2s re-check
 * runs only while paused. */
function useHiddenState(): [boolean, (v: boolean) => void] {
  const [hidden, setHidden] = useState(() => document.hidden)

  useEffect(() => {
    const onVis = () => setHidden(document.hidden)
    document.addEventListener('visibilitychange', onVis)
    let poll: ReturnType<typeof setInterval> | undefined
    if (document.hidden) {
      poll = setInterval(() => {
        if (!document.hidden) {
          setHidden(false)
          if (poll) clearInterval(poll)
        }
      }, 2000)
    }
    return () => {
      document.removeEventListener('visibilitychange', onVis)
      if (poll) clearInterval(poll)
    }
  }, [])

  return [hidden, setHidden]
}
