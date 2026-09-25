import PropTypes from 'prop-types'
import { useState } from 'react'

/**
 * AhpRadarChart: 7-Factor Comparative Spider / Radar Chart
 *
 * Visualizes the 7 research activity factors comparing an individual student
 * against the group average with pure SVG mathematics and zero external chart dependencies.
 */
export default function AhpRadarChart({
  factors = [],
  size = 360,
  studentLabel = 'You',
  groupLabel = 'Team Average',
}) {
  const [hoveredIndex, setHoveredIndex] = useState(null)

  const center = size / 2
  const radius = (size - 90) / 2
  const count = factors.length

  if (count === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-muted-foreground">
        No factor metrics available
      </div>
    )
  }

  // Calculate polygon coordinates for an array of values [0..100]
  const getCoordinates = (valueKey) => {
    return factors.map((f, i) => {
      const angle = (Math.PI * 2 * i) / count - Math.PI / 2
      const val = Math.max(0, Math.min(100, f[valueKey] || 0))
      const r = (val / 100) * radius
      const x = center + r * Math.cos(angle)
      const y = center + r * Math.sin(angle)
      return { x, y, val, label: f.label || f.name, weight: f.weight }
    })
  }

  const studentPoints = getCoordinates('studentValue')
  const groupPoints = getCoordinates('groupAvg')

  const studentPolygon = studentPoints.map((p) => `${p.x},${p.y}`).join(' ')
  const groupPolygon = groupPoints.map((p) => `${p.x},${p.y}`).join(' ')

  // Grid concentric rings at 25%, 50%, 75%, 100%
  const gridLevels = [0.25, 0.5, 0.75, 1.0]

  return (
    <div className="relative flex flex-col items-center">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="w-full max-w-[340px] h-auto overflow-visible select-none transition-all duration-300"
      >
        {/* Concentric Polygonal Background Grid */}
        {gridLevels.map((lvl) => {
          const ringPoints = factors
            .map((_, i) => {
              const angle = (Math.PI * 2 * i) / count - Math.PI / 2
              const r = radius * lvl
              const x = center + r * Math.cos(angle)
              const y = center + r * Math.sin(angle)
              return `${x},${y}`
            })
            .join(' ')
          return (
            <polygon
              key={`grid-${lvl}`}
              points={ringPoints}
              fill="none"
              className="stroke-border/50"
              strokeWidth="1"
              strokeDasharray={lvl === 1.0 ? '0' : '3 3'}
            />
          )
        })}

        {/* Axes lines from center to perimeter */}
        {factors.map((_, i) => {
          const angle = (Math.PI * 2 * i) / count - Math.PI / 2
          const x = center + radius * Math.cos(angle)
          const y = center + radius * Math.sin(angle)
          return (
            <line
              key={`axis-${i}`}
              x1={center}
              y1={center}
              x2={x}
              y2={y}
              className="stroke-border/60"
              strokeWidth="1"
            />
          )
        })}

        {/* Team Average Polygon (Background Reference) */}
        <polygon
          points={groupPolygon}
          className="fill-blue-500/15 stroke-blue-500"
          strokeWidth="2"
          strokeDasharray="4 4"
        />

        {/* Student Individual Polygon (Foreground Focus) */}
        <polygon
          points={studentPolygon}
          className="fill-primary/25 stroke-primary"
          strokeWidth="2.5"
        />

        {/* Data Points & Interactive Touch Targets */}
        {studentPoints.map((p, i) => (
          <g
            key={`student-pt-${i}`}
            onMouseEnter={() => setHoveredIndex(i)}
            onMouseLeave={() => setHoveredIndex(null)}
            className="cursor-pointer"
          >
            <circle
              cx={p.x}
              cy={p.y}
              r={hoveredIndex === i ? 6 : 4}
              className="fill-primary stroke-background transition-all duration-150"
              strokeWidth="2"
            />
            {/* Outer halo on hover */}
            {hoveredIndex === i && (
              <circle
                cx={p.x}
                cy={p.y}
                r={10}
                className="fill-primary/20 animate-ping"
              />
            )}
          </g>
        ))}

        {/* Outer Axis Labels */}
        {factors.map((f, i) => {
          const angle = (Math.PI * 2 * i) / count - Math.PI / 2
          const labelDist = radius + 32
          const x = center + labelDist * Math.cos(angle)
          const y = center + labelDist * Math.sin(angle)
          const isHovered = hoveredIndex === i

          return (
            <g key={`label-${i}`}>
              <text
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="central"
                className={`text-[10px] sm:text-[11px] font-medium transition-colors ${
                  isHovered
                    ? 'fill-primary font-bold'
                    : 'fill-muted-foreground'
                }`}
              >
                {f.label || f.name}
              </text>
            </g>
          )
        })}
      </svg>

      {/* Legend & Hover Data Capsule */}
      <div className="mt-3 flex flex-wrap items-center justify-center gap-4 text-xs">
        <div className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-primary ring-2 ring-primary/20" />
          <span className="font-semibold text-foreground">{studentLabel}</span>
        </div>
        <div className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-500 ring-2 ring-blue-500/20" />
          <span className="font-medium text-muted-foreground">{groupLabel}</span>
        </div>
      </div>

      {/* Dynamic Hover Details Pill */}
      {hoveredIndex !== null && factors[hoveredIndex] && (
        <div className="mt-2 px-3 py-1.5 rounded-md bg-card border border-border shadow-xs text-xs animate-fade-in flex items-center gap-3">
          <span className="font-semibold text-foreground">
            {factors[hoveredIndex].label || factors[hoveredIndex].name}
          </span>
          <span className="text-primary font-mono font-bold">
            {factors[hoveredIndex].studentValue}%
          </span>
          <span className="text-muted-foreground text-[11px]">
            (Team Avg: {factors[hoveredIndex].groupAvg}%)
          </span>
        </div>
      )}
    </div>
  )
}

AhpRadarChart.propTypes = {
  factors: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      label: PropTypes.string,
      studentValue: PropTypes.number,
      groupAvg: PropTypes.number,
      weight: PropTypes.number,
    }),
  ),
  size: PropTypes.number,
  studentLabel: PropTypes.string,
  groupLabel: PropTypes.string,
}
