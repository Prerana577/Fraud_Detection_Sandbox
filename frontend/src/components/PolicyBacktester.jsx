import React, { useState, useEffect } from 'react'
import { runBacktest, getConfig, updateConfig } from '../api'

/**
 * PolicyBacktester.jsx — "What-If" Rule Policy Simulation & Backtesting Studio.
 * Allows risk and compliance officers to simulate rule threshold changes
 * against historical transactions and measure the exact impact on fraud detection vs customer friction.
 */
export default function PolicyBacktester() {
  const [params, setParams] = useState({
    speed_threshold_kmh: 900,
    amount_multiplier: 3.0,
    max_txns: 5,
    window_seconds: 120,
    min_failures: 3,
    approve_max: 39,
    flag_max: 69,
    sample_limit: 500,
  })

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [appliedMsg, setAppliedMsg] = useState(null)

  // Load current production config on mount
  useEffect(() => {
    getConfig().then((cfg) => {
      if (cfg && cfg.impossible_travel) {
        setParams(prev => ({
          ...prev,
          speed_threshold_kmh: cfg.impossible_travel.speed_threshold_kmh || 900,
          amount_multiplier: cfg.amount_anomaly?.multiplier || 3.0,
          max_txns: cfg.velocity?.max_txns || 5,
          window_seconds: cfg.velocity?.window_seconds || 120,
          min_failures: cfg.repeated_failures?.min_failures || 3,
        }))
      }
    }).catch(() => {})
  }, [])

  const handleRunBacktest = async () => {
    setLoading(true)
    setError(null)
    setAppliedMsg(null)
    try {
      const res = await runBacktest(params)
      setResult(res)
    } catch (err) {
      setError(err.message || 'Failed to execute backtest simulation')
    } finally {
      setLoading(false)
    }
  }

  const handleApplyToProd = async () => {
    try {
      await updateConfig({
        impossible_travel: { speed_threshold_kmh: Number(params.speed_threshold_kmh) },
        amount_anomaly: { multiplier: Number(params.amount_multiplier) },
        velocity: { max_txns: Number(params.max_txns), window_seconds: Number(params.window_seconds) },
        repeated_failures: { min_failures: Number(params.min_failures) },
      })
      setAppliedMsg('✅ Simulated policy successfully promoted to Live Production Rule Engine!')
      setTimeout(() => setAppliedMsg(null), 5000)
    } catch (err) {
      setError('Failed to update live config: ' + err.message)
    }
  }

  return (
    <div style={{ padding: '4px 0 24px 0' }}>
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%)',
        border: '1px solid rgba(148, 163, 184, 0.15)',
        borderRadius: '12px',
        padding: '20px 24px',
        marginBottom: '20px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h2 style={{ margin: 0, fontWeight: 700, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: 8 }}>
              🧪 "What-If" Rule Policy Backtester & Impact Simulator
            </h2>
            <p style={{ margin: '6px 0 0 0', color: '#94a3b8', fontSize: '0.85rem' }}>
              Simulate rule adjustments across historical transactions before pushing to production. Assess detection delta & customer false alarm friction.
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleRunBacktest}
            disabled={loading}
            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', fontWeight: 700 }}
          >
            {loading ? '⏳ Evaluating Policy...' : '🚀 Run What-If Simulation'}
          </button>
        </div>

        {/* Sliders Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 16,
          marginTop: 20,
          background: 'rgba(15, 23, 42, 0.6)',
          padding: '16px',
          borderRadius: '8px',
          border: '1px solid rgba(255,255,255,0.05)'
        }}>
          {/* Speed Limit */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: 4 }}>
              <span style={{ color: '#cbd5e1', fontWeight: 600 }}>✈️ Speed Limit</span>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>{params.speed_threshold_kmh} km/h</span>
            </div>
            <input
              type="range"
              min="400"
              max="1500"
              step="50"
              value={params.speed_threshold_kmh}
              onChange={(e) => setParams({ ...params, speed_threshold_kmh: Number(e.target.value) })}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Baseline: 900 km/h (Commercial jet)</div>
          </div>

          {/* Amount Multiplier */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: 4 }}>
              <span style={{ color: '#cbd5e1', fontWeight: 600 }}>💰 Amount Multiplier</span>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>{params.amount_multiplier}× avg</span>
            </div>
            <input
              type="range"
              min="1.5"
              max="8.0"
              step="0.5"
              value={params.amount_multiplier}
              onChange={(e) => setParams({ ...params, amount_multiplier: Number(e.target.value) })}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Spike above user's rolling average</div>
          </div>

          {/* Velocity Burst */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: 4 }}>
              <span style={{ color: '#cbd5e1', fontWeight: 600 }}>⚡ Velocity Burst</span>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>&gt; {params.max_txns} txns / {params.window_seconds}s</span>
            </div>
            <input
              type="range"
              min="2"
              max="10"
              step="1"
              value={params.max_txns}
              onChange={(e) => setParams({ ...params, max_txns: Number(e.target.value) })}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Transactions within time window</div>
          </div>

          {/* Decision Thresholds */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: 4 }}>
              <span style={{ color: '#cbd5e1', fontWeight: 600 }}>🎯 Flag Threshold</span>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>Score &gt; {params.approve_max}</span>
            </div>
            <input
              type="range"
              min="20"
              max="60"
              step="5"
              value={params.approve_max}
              onChange={(e) => setParams({ ...params, approve_max: Number(e.target.value) })}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Score threshold triggering FLAG state</div>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', borderRadius: '8px', marginBottom: 16 }}>
          ⚠️ {error}
        </div>
      )}

      {appliedMsg && (
        <div style={{ padding: '12px 16px', background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', borderRadius: '8px', marginBottom: 16 }}>
          {appliedMsg}
        </div>
      )}

      {/* Backtest Results */}
      {result && result.status === 'success' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Recommendation Banner */}
          <div style={{
            background: 'linear-gradient(90deg, rgba(30, 58, 138, 0.4) 0%, rgba(17, 24, 39, 0.6) 100%)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            borderRadius: '10px',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12
          }}>
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>Policy Recommendation</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', marginTop: 2 }}>{result.impact.recommendation}</div>
            </div>
            <button
              className="btn btn-secondary"
              onClick={handleApplyToProd}
              style={{ background: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', borderColor: 'rgba(34, 197, 94, 0.4)' }}
            >
              📥 Promote Policy to Production
            </button>
          </div>

          {/* Comparison Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
            {/* Baseline Policy Card */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '10px',
              padding: '16px',
            }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8' }}>Baseline Production Policy</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: 4, color: '#f1f5f9' }}>
                {result.baseline.fraud_rate}% <span style={{ fontSize: '0.8rem', fontWeight: 400, color: '#94a3b8' }}>Fraud Rate</span>
              </div>
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.82rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Approved:</span>
                  <span style={{ color: '#4ade80', fontWeight: 600 }}>{result.baseline.approved}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Flagged for Review:</span>
                  <span style={{ color: '#fbbf24', fontWeight: 600 }}>{result.baseline.flagged}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Instant Blocks:</span>
                  <span style={{ color: '#f87171', fontWeight: 600 }}>{result.baseline.blocked}</span>
                </div>
              </div>
            </div>

            {/* Simulated Policy Card */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              borderRadius: '10px',
              padding: '16px',
              boxShadow: '0 0 15px rgba(56, 189, 248, 0.1)',
            }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#38bdf8' }}>Simulated New Policy</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: 4, color: '#38bdf8' }}>
                {result.simulated.fraud_rate}% <span style={{ fontSize: '0.8rem', fontWeight: 400, color: '#94a3b8' }}>Fraud Rate</span>
              </div>
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.82rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Approved:</span>
                  <span style={{ color: '#4ade80', fontWeight: 600 }}>{result.simulated.approved}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Flagged for Review:</span>
                  <span style={{ color: '#fbbf24', fontWeight: 600 }}>{result.simulated.flagged}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Instant Blocks:</span>
                  <span style={{ color: '#f87171', fontWeight: 600 }}>{result.simulated.blocked}</span>
                </div>
              </div>
            </div>

            {/* Impact Delta Card */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '10px',
              padding: '16px',
            }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8' }}>Simulated Net Delta</div>
              <div style={{
                fontSize: '1.4rem',
                fontWeight: 800,
                marginTop: 4,
                color: result.impact.fraud_interception_delta_pct >= 0 ? '#38bdf8' : '#f87171'
              }}>
                {result.impact.fraud_interception_delta_pct > 0 ? `+${result.impact.fraud_interception_delta_pct}%` : `${result.impact.fraud_interception_delta_pct}%`}
                <span style={{ fontSize: '0.8rem', fontWeight: 400, color: '#94a3b8' }}> Detection Delta</span>
              </div>
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.82rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Additional Blocks:</span>
                  <span style={{ color: '#f87171', fontWeight: 600 }}>
                    {result.impact.additional_blocks > 0 ? `+${result.impact.additional_blocks}` : result.impact.additional_blocks}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Additional Flags:</span>
                  <span style={{ color: '#fbbf24', fontWeight: 600 }}>
                    {result.impact.additional_flags > 0 ? `+${result.impact.additional_flags}` : result.impact.additional_flags}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Total Evaluated Txns:</span>
                  <span style={{ color: '#f1f5f9', fontWeight: 600 }}>{result.total_evaluated}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Reclassified Sample Table */}
          {result.reclassified_sample && result.reclassified_sample.length > 0 && (
            <div style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '10px',
              padding: '16px',
            }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '0.95rem', fontWeight: 700, color: '#f1f5f9' }}>
                Sample Reclassified Transactions Under Proposed Policy ({result.reclassified_sample.length})
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left', color: '#94a3b8' }}>
                      <th style={{ padding: '8px' }}>User / Merchant</th>
                      <th style={{ padding: '8px' }}>Amount</th>
                      <th style={{ padding: '8px' }}>City</th>
                      <th style={{ padding: '8px' }}>Baseline Decision</th>
                      <th style={{ padding: '8px' }}>Simulated Decision</th>
                      <th style={{ padding: '8px' }}>Simulated Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.reclassified_sample.map((row, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '8px' }}>
                          <div style={{ fontWeight: 600, color: '#f1f5f9' }}>{row.user_name}</div>
                          <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{row.merchant}</div>
                        </td>
                        <td style={{ padding: '8px', fontWeight: 600, color: '#f1f5f9' }}>₹{row.amount?.toLocaleString()}</td>
                        <td style={{ padding: '8px', color: '#cbd5e1' }}>{row.city}</td>
                        <td style={{ padding: '8px' }}>
                          <span className={`badge ${row.original_decision.toLowerCase()}`}>
                            {row.original_decision} ({row.original_score})
                          </span>
                        </td>
                        <td style={{ padding: '8px' }}>
                          <span className={`badge ${row.simulated_decision.toLowerCase()}`}>
                            {row.simulated_decision} ({row.simulated_score})
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#94a3b8', fontSize: '0.75rem' }}>
                          {row.reasons.join(', ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {result && result.status === 'empty' && (
        <div style={{
          background: 'rgba(15, 23, 42, 0.8)',
          border: '1px dashed rgba(255, 255, 255, 0.2)',
          borderRadius: '10px',
          padding: '32px',
          textAlign: 'center',
          color: '#94a3b8'
        }}>
          <span style={{ fontSize: '2rem' }}>📥</span>
          <h3 style={{ margin: '12px 0 6px 0', color: '#f1f5f9' }}>No Historical Transactions in Database</h3>
          <p style={{ margin: 0, fontSize: '0.85rem' }}>
            {result.message}
          </p>
        </div>
      )}
    </div>
  )
}
