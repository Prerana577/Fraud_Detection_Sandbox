/**
 * SettingsDrawer.jsx — Left-side drawer to edit rule thresholds live.
 * Changes are sent to PUT /api/config and take effect immediately.
 */
import { useState, useEffect } from 'react'
import { getConfig, updateConfig } from '../api'

const FIELDS = {
  impossible_travel: [
    { key: 'speed_threshold_kmh', label: 'Speed Threshold (km/h)', type: 'number' },
    { key: 'points', label: 'Points', type: 'number' },
  ],
  velocity: [
    { key: 'max_txns', label: 'Max Txns in Window', type: 'number' },
    { key: 'window_seconds', label: 'Window (seconds)', type: 'number' },
    { key: 'points', label: 'Points', type: 'number' },
  ],
  amount_anomaly: [
    { key: 'multiplier', label: 'Amount Multiplier', type: 'number', step: 0.1 },
    { key: 'zscore_threshold', label: 'Z-Score Threshold', type: 'number', step: 0.1 },
    { key: 'points', label: 'Points', type: 'number' },
  ],
  repeated_failures: [
    { key: 'min_failures', label: 'Min Failures', type: 'number' },
    { key: 'window_seconds', label: 'Window (seconds)', type: 'number' },
    { key: 'points', label: 'Points', type: 'number' },
  ],
}

const RULE_LABELS = {
  impossible_travel: '🚀 Impossible Travel',
  velocity:          '⚡ Velocity',
  amount_anomaly:    '💰 Amount Anomaly',
  repeated_failures: '❌ Repeated Failures',
}

export default function SettingsDrawer({ onClose }) {
  const [config, setConfig] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved,  setSaved]  = useState(false)

  useEffect(() => {
    getConfig().then(setConfig).catch(console.error)
  }, [])

  function handleChange(rule, key, val) {
    setConfig((prev) => ({
      ...prev,
      [rule]: { ...prev[rule], [key]: parseFloat(val) || val },
    }))
  }

  async function handleSave() {
    setSaving(true)
    try {
      await updateConfig(config)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      alert('Save failed: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-drawer" role="dialog" aria-modal="true" aria-label="Rule Settings">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: '1rem' }}>⚙️ Rule Settings</h2>
        <button className="detail-close" style={{ position: 'static' }} onClick={onClose} aria-label="Close settings">✕</button>
      </div>

      {!config ? (
        <p className="text-muted">Loading…</p>
      ) : (
        Object.entries(FIELDS).map(([rule, fields]) => (
          <div key={rule} className="settings-group">
            <p style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 10 }}>
              {RULE_LABELS[rule]}
            </p>
            {fields.map((f) => (
              <div key={f.key} style={{ marginBottom: 10 }}>
                <label htmlFor={`setting-${rule}-${f.key}`}>{f.label}</label>
                <input
                  id={`setting-${rule}-${f.key}`}
                  type={f.type}
                  step={f.step || 1}
                  value={config[rule]?.[f.key] ?? ''}
                  onChange={(e) => handleChange(rule, f.key, e.target.value)}
                  aria-label={`${RULE_LABELS[rule]} — ${f.label}`}
                />
              </div>
            ))}
          </div>
        ))
      )}

      <button
        className={`btn ${saved ? 'btn-success' : 'btn-primary'}`}
        style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}
        onClick={handleSave}
        disabled={saving || !config}
        id="save-settings-btn"
        aria-label="Save rule configuration"
      >
        {saving ? 'Saving…' : saved ? '✓ Saved!' : 'Save Changes'}
      </button>

      <p className="text-muted" style={{ marginTop: 12, fontSize: '0.72rem' }}>
        Changes apply immediately to all new transactions.
      </p>
    </div>
  )
}
