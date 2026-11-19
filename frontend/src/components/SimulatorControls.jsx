/**
 * SimulatorControls.jsx — Control bar for the transaction simulator and custom dataset uploader.
 */
import { useRef, useState } from 'react'
import { startSimulator, stopSimulator, setSimSpeed, injectPattern, uploadCsv } from '../api'

export default function SimulatorControls({ simStatus, onStatusChange, onError }) {
  const running = simStatus?.running ?? false
  const minDelay = simStatus?.min_delay ?? 0.5
  const maxDelay = simStatus?.max_delay ?? 2.0
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const fileInputRef = useRef(null)

  // Speed is represented as txns/sec for user-friendliness
  const speed = maxDelay > 0 ? (1 / ((minDelay + maxDelay) / 2)).toFixed(1) : 1

  async function handleStart() {
    try { onStatusChange(await startSimulator()) }
    catch (e) { onError(e.message) }
  }

  async function handleStop() {
    try { onStatusChange(await stopSimulator()) }
    catch (e) { onError(e.message) }
  }

  async function handleSpeedChange(e) {
    const tps = parseFloat(e.target.value)
    const delay = 1 / tps
    try { onStatusChange(await setSimSpeed(delay * 0.5, delay * 1.5)) }
    catch (e) { onError(e.message) }
  }

  async function inject(pattern) {
    try { await injectPattern(pattern) }
    catch (e) { onError(e.message) }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      setUploading(true)
      setUploadMsg(`Evaluating dataset ${file.name}…`)
      const res = await uploadCsv(file, true)
      const count = res.total_rows_evaluated ?? res.total_processed ?? 0
      const kaggleInfo = res.kaggle_evaluation ? ` • Accuracy: ${res.kaggle_evaluation.accuracy_pct}% • Frauds Caught: ${res.kaggle_evaluation.detected_frauds}/${res.kaggle_evaluation.actual_frauds_in_sample}` : ''
      setUploadMsg(`✓ Evaluated ${count} transactions (${res.counts?.FLAG || 0} flagged, ${res.counts?.BLOCK || 0} blocked)${kaggleInfo}`)
      setTimeout(() => setUploadMsg(null), 5000)
    } catch (err) {
      onError(`Upload failed: ${err.message}`)
      setUploadMsg(null)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div className="simulator-bar" role="region" aria-label="Simulator Controls">
        {/* Status indicator */}
        <div className="sim-status">
          <span className={`sim-dot ${running ? 'running' : 'stopped'}`} aria-hidden="true" />
          <span>{running ? 'Simulator Running' : 'Simulator Stopped'}</span>
        </div>

        {/* Speed slider */}
        <div className="speed-group">
          <label htmlFor="speed-slider">Speed:</label>
          <input
            id="speed-slider"
            type="range"
            min="0.2"
            max="5"
            step="0.1"
            defaultValue={speed}
            onChange={handleSpeedChange}
            aria-label="Transaction generation speed"
          />
          <span>~{speed} txn/s</span>
        </div>

        {/* Start/Stop */}
        {!running ? (
          <button className="btn btn-success" onClick={handleStart} id="sim-start-btn">
            ▶ Start
          </button>
        ) : (
          <button className="btn btn-danger" onClick={handleStop} id="sim-stop-btn">
            ■ Stop
          </button>
        )}

        {/* Inject fraud patterns */}
        <button
          className="btn btn-warning"
          onClick={() => inject('impossible_travel')}
          id="inject-travel-btn"
          title="Inject an impossible travel transaction"
        >
          ✈ Impossible Travel
        </button>
        <button
          className="btn btn-warning"
          onClick={() => inject('velocity_burst')}
          id="inject-velocity-btn"
          title="Inject 8 rapid transactions"
        >
          ⚡ Velocity Burst
        </button>
        <button
          className="btn btn-warning"
          onClick={() => inject('large_amount')}
          id="inject-amount-btn"
          title="Inject a transaction 8× the user's average"
        >
          💰 Large Amount
        </button>
        <button
          className="btn btn-ghost"
          onClick={() => inject('repeated_failures')}
          id="inject-failures-btn"
          title="Inject 4 failed transactions → account freeze"
        >
          ❌ Repeated Failures
        </button>

        {/* Upload Custom Dataset Button */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileUpload}
          accept=".csv"
          style={{ display: 'none' }}
          id="csv-file-input"
        />
        <button
          className="btn btn-secondary"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          id="upload-csv-btn"
          title="Upload and evaluate custom CSV dataset"
          style={{ marginLeft: 'auto' }}
        >
          {uploading ? '⏳ Evaluating…' : '📁 Upload Dataset (CSV)'}
        </button>
      </div>

      {uploadMsg && (
        <div style={{
          padding: '8px 16px',
          background: 'rgba(34, 197, 94, 0.1)',
          border: '1px solid var(--color-approve)',
          borderRadius: 'var(--radius)',
          color: 'var(--color-approve)',
          fontSize: '0.85rem',
          fontWeight: 600,
        }}>
          {uploadMsg}
        </div>
      )}
    </div>
  )
}
