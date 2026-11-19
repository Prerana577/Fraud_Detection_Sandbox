/**
 * DecisionDonut.jsx — Doughnut chart showing the APPROVE / FLAG / BLOCK split.
 * Uses react-chartjs-2.
 */
import { Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

export default function DecisionDonut({ stats }) {
  const s = stats || {}
  const approved = s.approved ?? 0
  const flagged  = s.flagged  ?? 0
  const blocked  = s.blocked  ?? 0
  const total    = approved + flagged + blocked

  const data = {
    labels: ['Approved', 'Flagged', 'Blocked'],
    datasets: [{
      data: [approved, flagged, blocked],
      backgroundColor: ['#067647', '#B54708', '#B42318'],
      borderColor:     ['#fff', '#fff', '#fff'],
      borderWidth: 2,
      hoverOffset: 6,
    }],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          font: { family: 'Inter', size: 12 },
          padding: 12,
          boxWidth: 12,
          boxHeight: 12,
        },
      },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0
            return ` ${ctx.label}: ${ctx.parsed} (${pct}%)`
          },
        },
      },
    },
  }

  return (
    <div className="card" style={{ height: 280 }}>
      <p className="card-title">Decision Split</p>
      {total === 0 ? (
        <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height: 200, color: 'var(--color-text-light)', fontSize: '0.85rem' }}>
          No data yet — start the simulator
        </div>
      ) : (
        <div style={{ height: 210, position: 'relative' }}>
          <Doughnut data={data} options={options} aria-label="Decision distribution donut chart" />
        </div>
      )}
    </div>
  )
}
