/**
 * Alerts.jsx — High-risk alert list (score >= 70) with toast notifications.
 * Props:
 *   alerts      — array from GET /simulator/alerts
 *   toasts      — recent alerts to show as toasts
 *   onDismiss   — called with alert id to acknowledge
 */
import { useEffect, useState } from 'react'

function relTime(iso) {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60)  return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export function Toast({ message, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 6000)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div className="toast" role="alert" aria-live="assertive">
      <strong>🚨 High-Risk Alert</strong>
      <p style={{ marginTop: 4, color: 'var(--color-text-muted)' }}>{message}</p>
      <button
        onClick={onDismiss}
        style={{ marginTop: 8, fontSize: '0.75rem', background: 'none', border: 'none',
                 color: 'var(--color-accent)', cursor: 'pointer', padding: 0 }}
      >
        Dismiss
      </button>
    </div>
  )
}

export function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="toast-container" aria-label="Alert notifications">
      {toasts.map((t) => (
        <Toast key={t.id} message={t.message} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  )
}

export default function Alerts({ alerts, onDismiss }) {
  return (
    <div className="card" style={{ maxHeight: 340, overflow: 'auto' }}>
      <p className="card-title">High-Risk Alerts</p>
      {(!alerts || alerts.length === 0) ? (
        <p className="text-muted" style={{ marginTop: 8 }}>No alerts yet.</p>
      ) : (
        alerts.map((a) => (
          <div key={a.id} className="alert-item" style={{ opacity: a.acknowledged ? 0.5 : 1 }}>
            <span className="alert-icon">🚨</span>
            <div>
              <p className="alert-msg">{a.message}</p>
              <p className="alert-time">{relTime(a.created_at)}</p>
            </div>
            {!a.acknowledged && (
              <button
                onClick={() => onDismiss(a.id)}
                className="btn btn-ghost"
                style={{ marginLeft: 'auto', fontSize: '0.72rem', padding: '4px 8px', flexShrink: 0 }}
                aria-label="Acknowledge alert"
              >
                ✓
              </button>
            )}
          </div>
        ))
      )}
    </div>
  )
}
