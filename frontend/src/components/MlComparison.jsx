/**
 * MlComparison.jsx — Side-by-side comparison between deterministic Rules and IsolationForest ML.
 * Tab: ML Comparison
 */
import { useState, useEffect, useCallback } from 'react'
import { getMlComparison, retrainMl, getMlMetrics, retrainRf } from '../api'

const fmt = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)

export default function MlComparison() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [retraining, setRetraining] = useState(false)
  const [msg, setMsg] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [retrainingRf, setRetrainingRf] = useState(false)
  const [rfMsg, setRfMsg] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const res = await getMlComparison({ limit: 50 })
      setData(res)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRetrain = async () => {
    try {
      setRetraining(true)
      setMsg(null)
      const res = await retrainMl()
      setMsg(res.message)
      await fetchData()
    } catch (err) {
      setMsg('Retraining failed: ' + err.message)
    } finally {
      setRetraining(false)
    }
  }

  if (loading && !data) {
    return <div className="panel" style={{ padding: 32, textAlign: 'center' }}>Loading ML Analysis…</div>
  }

  const matrix = data?.matrix || {}
  const comparisons = data?.comparisons || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontWeight: 700, fontSize: '1.25rem' }}>🤖 Rules vs IsolationForest (ML) Benchmark</h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', marginTop: 4 }}>
            Unsupervised outlier detection evaluated against expert deterministic rules
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={handleRetrain}
          disabled={retraining}
          id="retrain-ml-btn"
        >
          {retraining ? 'Retraining…' : '🔄 Retrain Model'}
        </button>
      </div>

      {msg && (
        <div style={{
          padding: '10px 16px',
          borderRadius: 'var(--radius)',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          color: 'var(--color-approve)',
          fontSize: '0.85rem'
        }}>
          ✓ {msg}
        </div>
      )}

      {/* KPI summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        <div className="card">
          <div className="card-label">Model Agreement Rate</div>
          <div className="card-value" style={{ color: 'var(--color-primary)' }}>
            {data?.agreement_rate ?? 0}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
            Rules and ML agreed on classification
          </div>
        </div>

        <div className="card">
          <div className="card-label">High-Confidence Fraud (Both)</div>
          <div className="card-value" style={{ color: 'var(--color-block)' }}>
            {matrix.both_flagged ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
            Confirmed by both engine & model
          </div>
        </div>

        <div className="card">
          <div className="card-label">Rules-Only Flags</div>
          <div className="card-value" style={{ color: 'var(--color-flag)' }}>
            {matrix.rules_only ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
            Blocked by rules (e.g. travel speed/velocity)
          </div>
        </div>

        <div className="card">
          <div className="card-label">ML-Only Outliers</div>
          <div className="card-value" style={{ color: 'var(--color-accent)' }}>
            {matrix.ml_only ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
            Subtle statistical multi-dim deviations
          </div>
        </div>
      </div>

      {/* Comparison table */}
      <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)', fontWeight: 600 }}>
          Recent Transaction Evaluation (Last {comparisons.length})
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="feed-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Txn ID</th>
                <th>Amount</th>
                <th>City / Merchant</th>
                <th>Rule Score</th>
                <th>Rule Decision</th>
                <th>ML Score</th>
                <th>ML Decision</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map((c) => {
                const isBothFlagged = c.comparison_status === 'AGREED_FRAUD'
                const isDisagreement = c.comparison_status === 'RULES_ONLY' || c.comparison_status === 'ML_ONLY'

                return (
                  <tr key={c.txn_id} style={{
                    background: isBothFlagged ? 'rgba(239, 68, 68, 0.08)' : isDisagreement ? 'rgba(234, 179, 8, 0.05)' : undefined
                  }}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{c.txn_id.slice(0, 8)}…</td>
                    <td style={{ fontWeight: 600 }}>{fmt(c.amount)}</td>
                    <td>{c.city} • <span style={{ color: 'var(--color-text-muted)' }}>{c.merchant}</span></td>
                    <td>
                      <span style={{ fontWeight: 600 }}>{c.rule_score}</span>/100
                    </td>
                    <td>
                      <span className={`badge badge-${c.rule_decision.toLowerCase()}`}>
                        {c.rule_decision}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600 }}>{c.ml_anomaly_score}</span>/100
                    </td>
                    <td>
                      <span className={`badge ${c.ml_decision === 'ANOMALY' ? 'badge-block' : 'badge-approve'}`}>
                        {c.ml_decision}
                      </span>
                    </td>
                    <td>
                      {c.comparison_status === 'AGREED_FRAUD' && (
                        <span style={{ color: 'var(--color-block)', fontWeight: 600, fontSize: '0.8rem' }}>🎯 High Risk (Agreed)</span>
                      )}
                      {c.comparison_status === 'AGREED_NORMAL' && (
                        <span style={{ color: 'var(--color-approve)', fontSize: '0.8rem' }}>✓ Clean</span>
                      )}
                      {c.comparison_status === 'RULES_ONLY' && (
                        <span style={{ color: 'var(--color-flag)', fontSize: '0.8rem' }}>⚡ Rules Caught</span>
                      )}
                      {c.comparison_status === 'ML_ONLY' && (
                        <span style={{ color: 'var(--color-accent)', fontSize: '0.8rem' }}>🧠 ML Outlier</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
