/**
 * LiveFeed.jsx — Real-time transaction table.
 * New rows animate in at the top; blocked rows are tinted red.
 * Click any row to open the BlockedDetail panel.
 */
import { memo } from 'react'

// Format amount in Indian Rupees
const fmt = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)

function RiskBar({ score, decision }) {
  const cls = decision === 'APPROVE' ? 'approve' : decision === 'FLAG' ? 'flag' : 'block'
  return (
    <div className="risk-bar-wrap">
      <div className="risk-bar-bg" role="progressbar" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100}>
        <div className={`risk-bar-fill ${cls}`} style={{ width: `${score}%` }} />
      </div>
      <span className={`risk-score-num`} style={{ color: `var(--color-${cls === 'approve' ? 'approve' : cls})` }}>
        {score}
      </span>
    </div>
  )
}

function Badge({ decision }) {
  return <span className={`badge ${decision}`}>{decision}</span>
}

function TimeStamp({ iso }) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleTimeString('en-IN', { hour12: false })
}

const LiveFeed = memo(function LiveFeed({ transactions, onSelectTxn }) {
  return (
    <div className="card" style={{ padding: 0 }}>
      <div style={{ padding: '16px 20px 12px', borderBottom: '1px solid var(--color-border)' }}>
        <p className="card-title" style={{ margin: 0 }}>Live Transaction Feed</p>
      </div>
      <div className="feed-table-wrap">
        <table className="feed-table" aria-label="Live transactions">
          <thead>
            <tr>
              <th>Time</th>
              <th>Txn ID</th>
              <th>User</th>
              <th>Amount</th>
              <th>City</th>
              <th>Device / IP</th>
              <th>Risk</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-light)' }}>
                  No transactions yet. Start the simulator →
                </td>
              </tr>
            ) : (
              transactions.map((txn) => {
                const rowCls =
                  txn.decision === 'BLOCK' ? 'row-block' :
                  txn.decision === 'FLAG'  ? 'row-flag' : ''
                return (
                  <tr
                    key={txn.txn_id}
                    className={rowCls}
                    onClick={() => onSelectTxn(txn)}
                    title="Click for details"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && onSelectTxn(txn)}
                    aria-label={`Transaction ${txn.txn_id.slice(0,8)}, ${txn.decision}`}
                  >
                    <td style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--color-text-muted)' }}>
                      <TimeStamp iso={txn.timestamp} />
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.78rem' }}>
                      {txn.txn_id.slice(0, 8)}…
                    </td>
                    <td className="truncate" style={{ maxWidth: 120 }}>{txn.user_name}</td>
                    <td style={{ fontWeight: 600 }}>{fmt(txn.amount)}</td>
                    <td>{txn.city}</td>
                    <td>
                      {txn.device_info ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                          <span>{txn.device_info.device_type?.includes('Mobile') ? '📱' : txn.device_info.device_type?.includes('Tor') ? '🧅' : '💻'}</span>
                          <span style={{
                            color: txn.device_info.vpn_detected ? '#f87171' : 'var(--color-text-muted)',
                            fontWeight: txn.device_info.vpn_detected ? 700 : 400
                          }}>
                            {txn.device_info.vpn_detected ? '🛡️ VPN' : (txn.device_info.device_type?.split(' ')[0] || 'Mobile')}
                          </span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>—</span>
                      )}
                    </td>
                    <td style={{ minWidth: 120 }}>
                      <RiskBar score={txn.risk_score} decision={txn.decision} />
                    </td>
                    <td><Badge decision={txn.decision} /></td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
})

export default LiveFeed
