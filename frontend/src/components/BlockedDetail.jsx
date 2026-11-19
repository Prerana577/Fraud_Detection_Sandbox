/**
 * BlockedDetail.jsx — Slide-in right panel explaining why a transaction was scored.
 * Includes admin quick actions: Approve, Block, Freeze User.
 */
import { useState } from 'react'
import { overrideTransaction, freezeUser } from '../api'
import StepUpModal from './StepUpModal'

const RULE_NAMES = {
  impossible_travel: '🚀 Impossible Travel',
  velocity:          '⚡ Velocity Burst',
  amount_anomaly:    '💰 Amount Anomaly',
  repeated_failures: '❌ Repeated Failures',
}

const fmt = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)

function generateAiBriefing(txn) {
  const reasons = txn.reasons || []
  const name = txn.user_name || txn.user_id
  const amt = fmt(txn.amount)

  if (reasons.length === 0) {
    return `Transaction of ${amt} at ${txn.merchant} in ${txn.city} aligns with cardholder ${name}'s verified baseline spending profile. Zero heuristic anomalies triggered. Risk evaluated as nominal.`
  }

  const details = reasons.map(r => r.detail).join(' Additionally, ')
  const isHighRisk = txn.risk_score >= 70

  return `Investigative Briefing: Cardholder ${name} triggered ${reasons.length} risk heuristic(s) for a ${amt} spend at ${txn.merchant} (${txn.city}). Primary anomaly flags: ${details}. ${
    isHighRisk
      ? 'Critical Threat: Transaction severely breaches behavioral bounds. Automated settlement block enforced to prevent capital loss.'
      : 'Moderate Anomaly: Borderline variance detected. Risk-Based Step-Up Authentication (3DS OTP challenge) recommended before clearance.'
  }`
}

export default function BlockedDetail({ txn, onClose, onActionComplete }) {
  const [actionMsg, setActionMsg] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showStepUp, setShowStepUp] = useState(false)

  if (!txn) return null

  const reasons = txn.reasons || []
  const decision = txn.decision

  async function handleAction(type) {
    try {
      setLoading(true)
      if (type === 'APPROVE' || type === 'BLOCK') {
        await overrideTransaction(txn.txn_id, type)
        setActionMsg(`✓ Transaction successfully overridden to ${type}!`)
      } else if (type === 'FREEZE') {
        await freezeUser(txn.user_id)
        setActionMsg(`❄️ User ${txn.user_name || txn.user_id} account frozen!`)
      }
      if (onActionComplete) onActionComplete()
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="detail-panel" role="dialog" aria-modal="true" aria-label="Transaction details">
      <button className="detail-close" onClick={onClose} aria-label="Close panel">✕</button>

      <h2>Transaction Audit</h2>
      <p className="text-muted" style={{ marginBottom: 16 }}>
        {txn.txn_id?.slice(0, 8)}… · {txn.user_name || txn.user_id}
      </p>

      {/* Meta info */}
      <div style={{ background: 'var(--color-bg)', borderRadius: 8, padding: 14, marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '0.82rem' }}>
          <div><span style={{ color: 'var(--color-text-muted)' }}>Amount</span><br /><strong>{fmt(txn.amount)}</strong></div>
          <div><span style={{ color: 'var(--color-text-muted)' }}>Merchant</span><br /><strong>{txn.merchant}</strong></div>
          <div><span style={{ color: 'var(--color-text-muted)' }}>City</span><br /><strong>{txn.city}</strong></div>
          <div><span style={{ color: 'var(--color-text-muted)' }}>Decision</span><br />
            <span className={`badge ${decision}`}>{decision}</span>
          </div>
        </div>
      </div>

      {/* Action feedback */}
      {actionMsg && (
        <div style={{
          padding: '8px 12px',
          background: 'rgba(34, 197, 94, 0.1)',
          border: '1px solid var(--color-approve)',
          borderRadius: 'var(--radius)',
          color: 'var(--color-approve)',
          fontSize: '0.8rem',
          fontWeight: 600,
          marginBottom: 16
        }}>
          {actionMsg}
        </div>
      )}

      {/* Admin Quick Action Bar */}
      <div style={{ marginBottom: 18, padding: 12, background: 'rgba(255,255,255,0.03)', borderRadius: 8, border: '1px solid var(--color-border)' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 8 }}>
          ADMIN ACTION CONTROLS & STEP-UP 2FA
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            className="btn btn-success"
            style={{ fontSize: '0.75rem', padding: '6px 12px' }}
            disabled={loading}
            onClick={() => handleAction('APPROVE')}
          >
            ✓ Approve
          </button>
          <button
            className="btn btn-danger"
            style={{ fontSize: '0.75rem', padding: '6px 12px' }}
            disabled={loading}
            onClick={() => handleAction('BLOCK')}
          >
            ✕ Block
          </button>
          <button
            className="btn btn-warning"
            style={{ fontSize: '0.75rem', padding: '6px 12px' }}
            disabled={loading}
            onClick={() => setShowStepUp(true)}
            title="Prompt cardholder with RuPay/Visa 3D-Secure OTP verification"
          >
            🛡️ 3DS Challenge
          </button>
          <button
            className="btn btn-ghost"
            style={{ fontSize: '0.75rem', padding: '6px 12px', color: 'var(--color-block)' }}
            disabled={loading}
            onClick={() => handleAction('FREEZE')}
          >
            ❄️ Freeze Account
          </button>
        </div>
      </div>

      {/* AI Analyst Briefing Card */}
      <div style={{
        marginBottom: 18,
        padding: 12,
        background: 'rgba(56, 189, 248, 0.08)',
        border: '1px solid rgba(56, 189, 248, 0.3)',
        borderRadius: 8,
      }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          🤖 AI ANALYST BRIEFING (EXPLAINABLE AI)
        </div>
        <p style={{ fontSize: '0.8rem', color: '#e2e8f0', lineHeight: 1.45 }}>
          {generateAiBriefing(txn)}
        </p>
      </div>

      {showStepUp && (
        <StepUpModal
          txn={txn}
          onClose={() => setShowStepUp(false)}
          onSuccess={() => {
            if (onActionComplete) onActionComplete()
          }}
        />
      )}

      {/* Rules that fired */}
      <p className="card-title">Scoring Breakdown</p>

      {reasons.length === 0 ? (
        <p className="text-muted" style={{ marginTop: 8 }}>
          ✅ No rules fired — clean transaction.
        </p>
      ) : (
        reasons.map((r, i) => (
          <div key={i} className="reason-item">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span className="reason-rule">{RULE_NAMES[r.rule] || r.rule}</span>
              <span className="reason-pts">+{r.points} pts</span>
            </div>
            <p className="reason-detail">{r.detail}</p>
          </div>
        ))
      )}

      {/* Total score */}
      <div className={`score-total`} style={{
        marginTop: 16,
        background: decision === 'APPROVE' ? 'var(--color-approve-bg)' :
                    decision === 'FLAG'    ? 'var(--color-flag-bg)'    : 'var(--color-block-bg)',
        color:      decision === 'APPROVE' ? 'var(--color-approve)' :
                    decision === 'FLAG'    ? 'var(--color-flag)'    : 'var(--color-block)',
      }}>
        Risk Score: {txn.risk_score} / 100
        <div style={{ fontSize: '0.8rem', fontWeight: 500, marginTop: 4 }}>
          {decision === 'APPROVE' ? '0–39 = APPROVE' :
           decision === 'FLAG'    ? '40–69 = FLAG'   : '70–100 = BLOCK'}
        </div>
      </div>
    </div>
  )
}
