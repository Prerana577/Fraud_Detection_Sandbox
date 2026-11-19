/**
 * RuleBars.jsx — Horizontal bar chart showing per-rule trigger counts.
 */
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const RULE_LABELS = {
  impossible_travel:  'Impossible Travel',
  velocity:           'Velocity Burst',
  amount_anomaly:     'Amount Anomaly',
  repeated_failures:  'Repeated Failures',
}

export default function RuleBars({ stats }) {
  const triggers = stats?.rule_triggers ?? {}
  const rules  = Object.keys(RULE_LABELS)
  const counts = rules.map((r) => triggers[r] ?? 0)

  const data = {
    labels: rules.map((r) => RULE_LABELS[r]),
    datasets: [{
      label: 'Triggers',
      data: counts,
      backgroundColor: ['#0F766E', '#B54708', '#B42318', '#7C3AED'],
      borderRadius: 6,
      borderSkipped: false,
    }],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => ` ${ctx.parsed.x} times`,
        },
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: { precision: 0, font: { family: 'Inter', size: 11 } },
        grid: { color: '#F1F5F9' },
      },
      y: {
        ticks: { font: { family: 'Inter', size: 11 } },
        grid: { display: false },
      },
    },
  }

  return (
    <div className="card" style={{ height: 280 }}>
      <p className="card-title">Rule Triggers</p>
      <div style={{ height: 210 }}>
        <Bar data={data} options={options} aria-label="Rule trigger count bar chart" />
      </div>
    </div>
  )
}
