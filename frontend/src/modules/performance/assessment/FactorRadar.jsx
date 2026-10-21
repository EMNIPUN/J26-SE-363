import PropTypes from 'prop-types'
import { Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts'
import { radarData } from './format.js'

/**
 * The student's factors on one chart, one spoke each, from 0 (centre) to 100 (edge), with the team average drawn over it to compare.
 * A factor that could not be measured has no score: it sits at the centre and is listed under the chart, never drawn as a bad score.
 */
export default function FactorRadar({ result, radar, average }) {
  const data = (result?.factors ? radarData(result, average) : null) || radar?.axes || result?.radar?.axes || []
  const missing = data.filter((d) => !d.measured)
  const hasAverage = data.some((d) => d.average != null)
  return (
    <div className="space-y-3">
      <div className="h-[26rem]" role="img" aria-label={`Factor scores: ${data.filter((d) => d.measured).map((d) => `${d.factor} ${d.score}`).join(', ')}`}>
        <ResponsiveContainer>
          <RadarChart data={data} outerRadius="80%" margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
            <PolarGrid gridType="polygon" />
            <PolarAngleAxis dataKey="short" tick={{ fontSize: 12, fill: 'currentColor' }} />
            <PolarRadiusAxis angle={90} domain={[0, 100]} tickCount={5} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} />
            {hasAverage && <Radar name="Team average" dataKey="average" stroke="#64748b" strokeWidth={2} strokeDasharray="5 4" fill="#64748b" fillOpacity={0.08} dot={false} />}
            <Radar name="This student" dataKey="score" stroke="#4f46e5" strokeWidth={2.5} fill="#6366f1" fillOpacity={0.3} dot={{ r: 3.5, fill: '#4f46e5' }} />
            <Tooltip formatter={(v, name, item) => (name === 'This student' && !item.payload.measured ? ['not measured', name] : [v, name])} labelFormatter={(_, items) => items?.[0]?.payload?.factor} />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      {missing.length > 0 && (
        <p className="rounded-lg bg-muted/50 p-3 text-xs leading-relaxed text-muted-foreground">
          Not on the chart because there is no score for it yet: {missing.map((d) => `${d.factor} (${(d.state || d.status || 'not measured').toLowerCase()})`).join(', ')}. It is left out of the mark, not counted as zero.
        </p>
      )}
    </div>
  )
}
FactorRadar.propTypes = { result: PropTypes.object, average: PropTypes.object, radar: PropTypes.object }
