interface MiniChartProps {
  data: number[]
  color?: string
  height?: number
  width?: number
}

export function MiniChart({ data, color = '#7c3aed', height = 32, width = 80 }: MiniChartProps) {
  if (!data.length) return null
  const max = Math.max(...data, 1)
  const points = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - (v / max) * height}`).join(' ')
  return (
    <svg width={width} height={height} className="flex-shrink-0">
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  )
}
