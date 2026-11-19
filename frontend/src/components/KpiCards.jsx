/**
 * KpiCards.jsx — Six summary metric cards across the top of the dashboard.
 * Props: stats (object from GET /api/stats)
 */
export default function KpiCards({ stats }) {
  const s = stats || {}

  const cards = [
    { label: 'Total Transactions', value: s.total ?? '—',          cls: '' },
    { label: 'Approved',           value: s.approved ?? '—',       cls: 'approve' },
    { label: 'Flagged',            value: s.flagged ?? '—',        cls: 'flag' },
    { label: 'Blocked',            value: s.blocked ?? '—',        cls: 'block' },
    { label: 'Fraud Rate',         value: s.fraud_rate != null ? `${s.fraud_rate}%` : '—', cls: 'accent' },
    { label: 'Frozen Accounts',    value: s.frozen_accounts ?? '—', cls: 'frozen' },
  ]

  return (
    <div className="kpi-grid" role="region" aria-label="Key Performance Indicators">
      {cards.map((c) => (
        <div key={c.label} className="kpi-card">
          <span className="kpi-label">{c.label}</span>
          <span className={`kpi-value ${c.cls}`} aria-label={`${c.label}: ${c.value}`}>
            {c.value}
          </span>
          {c.label === 'Fraud Rate' && (
            <span className="kpi-sub">flags + blocks</span>
          )}
          {c.label === 'Total Transactions' && s.avg_risk_score != null && (
            <span className="kpi-sub">avg risk: {s.avg_risk_score}/100</span>
          )}
        </div>
      ))}
    </div>
  )
}
