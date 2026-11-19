import { useState } from 'react'
import { overrideTransaction, freezeUser } from '../api'

export default function StepUpModal({ txn, onClose, onSuccess }) {
  const [otpInput, setOtpInput] = useState('')
  const [attempts, setAttempts] = useState(0)
  const [errorMsg, setErrorMsg] = useState(null)
  const [verified, setVerified] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Demo OTP for instant demonstration
  const validOtp = '739215'

  const handleVerify = async (e) => {
    e?.preventDefault()
    if (!otpInput.trim()) return

    if (otpInput.trim() === validOtp) {
      setSubmitting(true)
      try {
        await overrideTransaction(txn.txn_id, 'APPROVE')
        setVerified(true)
        setTimeout(() => {
          onSuccess?.()
          onClose?.()
        }, 1800)
      } catch (err) {
        setErrorMsg(err.message)
      } finally {
        setSubmitting(false)
      }
    } else {
      const nextAttempts = attempts + 1
      setAttempts(nextAttempts)
      setOtpInput('')

      if (nextAttempts >= 3) {
        setSubmitting(true)
        setErrorMsg('❌ 3 consecutive OTP failures! Automated Card Lock Triggered.')
        try {
          await overrideTransaction(txn.txn_id, 'BLOCK')
          if (txn.user_id) await freezeUser(txn.user_id)
          setTimeout(() => {
            onSuccess?.()
            onClose?.()
          }, 2500)
        } catch (err) {
          console.error(err)
        } finally {
          setSubmitting(false)
        }
      } else {
        setErrorMsg(`Incorrect OTP. ${3 - nextAttempts} attempt(s) remaining before account lockout.`)
      }
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2000,
    }}>
      <div style={{
        background: '#0f172a',
        border: '1px solid #334155',
        borderRadius: 16,
        width: '460px',
        maxWidth: '92vw',
        padding: 24,
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
        display: 'flex',
        flexDirection: 'column',
        gap: 18,
      }}>
        {/* 3D-Secure Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '1.4rem' }}>🛡️</span>
            <div>
              <div style={{ fontWeight: 800, fontSize: '0.95rem', letterSpacing: 0.5, color: '#f8fafc' }}>
                RuPay / Visa 3D-Secure 2.0
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Risk-Based Step-Up Authentication (RBA)</div>
            </div>
          </div>
          <button className="btn btn-ghost" onClick={onClose} style={{ padding: '2px 8px', fontSize: '1rem' }}>✕</button>
        </div>

        {/* Transaction Brief */}
        <div style={{ background: '#1e293b', padding: 14, borderRadius: 10, fontSize: '0.82rem', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Merchant:</span>
            <span style={{ fontWeight: 700 }}>{txn.merchant}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Amount:</span>
            <span style={{ fontWeight: 800, color: '#38bdf8', fontSize: '1rem' }}>₹{txn.amount?.toLocaleString()}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Cardholder:</span>
            <span>{txn.user_name || txn.user_id}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Initial Risk Tier:</span>
            <span style={{ color: '#f59e0b', fontWeight: 700 }}>FLAG (Score: {txn.risk_score}/100)</span>
          </div>
        </div>

        {verified ? (
          <div style={{ textAlign: 'center', padding: '16px 0', color: '#4ade80' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>✓</div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>Identity Verified Successfully!</div>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: 4 }}>Transaction approved via 3DS 2.0 Step-Up Challenge.</div>
          </div>
        ) : (
          <form onSubmit={handleVerify} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.4 }}>
              A high-risk anomaly was flagged. A 6-digit One-Time Passcode (OTP) has been dispatched to cardholder's registered mobile ending in <strong>•••• 89</strong>.
            </p>

            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                maxLength={6}
                value={otpInput}
                onChange={(e) => setOtpInput(e.target.value.replace(/\D/g, ''))}
                placeholder="Enter 6-digit OTP"
                disabled={submitting || attempts >= 3}
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: '#090d16',
                  border: '1px solid #475569',
                  color: '#fff',
                  fontSize: '1.1rem',
                  letterSpacing: 4,
                  textAlign: 'center',
                  fontWeight: 'bold',
                }}
              />
              <button
                type="button"
                className="btn btn-ghost"
                style={{ fontSize: '0.75rem', padding: '6px 10px', whiteSpace: 'nowrap' }}
                onClick={() => setOtpInput(validOtp)}
                title="Fill with simulated test OTP"
              >
                Auto-fill ({validOtp})
              </button>
            </div>

            {errorMsg && (
              <div style={{
                padding: '8px 12px',
                borderRadius: 6,
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#f87171',
                fontSize: '0.78rem',
                fontWeight: 600,
              }}>
                {errorMsg}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={onClose}
                style={{ flex: 1 }}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                style={{ flex: 2, fontWeight: 700 }}
                disabled={submitting || otpInput.length < 6 || attempts >= 3}
              >
                {submitting ? 'Verifying…' : 'Verify & Approve'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
