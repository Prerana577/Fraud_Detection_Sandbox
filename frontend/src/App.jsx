/**
 * App.jsx — Root component.
 *
 * Responsibilities:
 *  • Manages WebSocket subscription (new_transaction, new_alert, stats_update)
 *  • Polls /api/stats every 10 s as a fallback
 *  • Owns global state: transactions[], stats{}, alerts[], simStatus{}
 *  • Renders the tab-based layout: Dashboard | Flagged | Admin | Simulator
 *  • Orchestrates BlockedDetail panel, SettingsDrawer, and ToastContainer
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import socket from './socket'
import { getTransactions, getStats, getAlerts, getSimStatus, acknowledgeAlert, resetDatabase } from './api'

import KpiCards          from './components/KpiCards'
import LiveFeed          from './components/LiveFeed'
import DecisionDonut     from './components/DecisionDonut'
import RuleBars          from './components/RuleBars'
import BlockedDetail     from './components/BlockedDetail'
import Alerts, { ToastContainer } from './components/Alerts'
import AdminPanel        from './components/AdminPanel'
import SimulatorControls from './components/SimulatorControls'
import SettingsDrawer    from './components/SettingsDrawer'
import MlComparison      from './components/MlComparison'
import GeoMap            from './components/GeoMap'
import RingVisualizer    from './components/RingVisualizer'
import SlaSpeedometer    from './components/SlaSpeedometer'
import PolicyBacktester  from './components/PolicyBacktester'

const MAX_FEED_ROWS = 200  // keep the last 200 transactions in memory

// ── Native Web Audio & Voice Synthesizer ─────────────────────────────────────
function playAlarmChime(isBlock = true) {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    if (ctx.state === 'suspended') ctx.resume()

    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = isBlock ? 'sawtooth' : 'sine'
    osc.frequency.setValueAtTime(isBlock ? 880 : 587, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(isBlock ? 440 : 880, ctx.currentTime + 0.3)
    gain.gain.setValueAtTime(0.2, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.3)
  } catch (e) {
    console.debug('Audio unavailable', e)
  }
}

function announceVoice(text) {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 1.05
      utterance.pitch = 1.0
      utterance.volume = 0.9
      window.speechSynthesis.speak(utterance)
    } catch (e) {
      console.debug('Voice unavailable', e)
    }
  }
}

export default function App() {
  const [activeTab,     setActiveTab]     = useState('dashboard')
  const [transactions,  setTransactions]  = useState([])
  const [stats,         setStats]         = useState(null)
  const [alerts,        setAlerts]        = useState([])
  const [toasts,        setToasts]        = useState([])
  const [simStatus,     setSimStatus]     = useState({ running: false })
  const [selectedTxn,   setSelectedTxn]   = useState(null)
  const [showSettings,  setShowSettings]  = useState(false)
  const [voiceEnabled,  setVoiceEnabled]  = useState(true)
  const [error,         setError]         = useState(null)

  const toastIdRef = useRef(0)
  const lastAnnounceRef = useRef(0)

  // ── Refresh helpers ───────────────────────────────────────────────────────
  const refreshStats = useCallback(async () => {
    try   { setStats(await getStats()) }
    catch  {}
  }, [])

  const refreshAlerts = useCallback(async () => {
    try   { setAlerts(await getAlerts()) }
    catch  {}
  }, [])

  const refreshSimStatus = useCallback(async () => {
    try   { setSimStatus(await getSimStatus()) }
    catch  {}
  }, [])

  // ── Initial load ──────────────────────────────────────────────────────────
  useEffect(() => {
    async function boot() {
      try {
        const [txns, s, al, sim] = await Promise.all([
          getTransactions({ limit: 50 }),
          getStats(),
          getAlerts(),
          getSimStatus(),
        ])
        setTransactions(txns)
        setStats(s)
        setAlerts(al)
        setSimStatus(sim)
      } catch (e) {
        setError('Backend not reachable. Is Flask running on port 5001?')
      }
    }
    boot()
  }, [])

  // ── Stats polling fallback (every 10 s) ──────────────────────────────────
  useEffect(() => {
    const id = setInterval(refreshStats, 10_000)
    return () => clearInterval(id)
  }, [refreshStats])

  // ── WebSocket listeners ───────────────────────────────────────────────────
  useEffect(() => {
    function onNewTxn(txn) {
      setTransactions((prev) => [txn, ...prev].slice(0, MAX_FEED_ROWS))
      // Refresh stats on every new txn (lightweight — no round-trip if WS stats_update fires)
      refreshStats()

      // Real-time audio siren & voice announcement
      if (voiceEnabled) {
        if (txn.decision === 'BLOCK') {
          playAlarmChime(true)
          const now = Date.now()
          if (now - lastAnnounceRef.current > 3500) {
            lastAnnounceRef.current = now
            const name = txn.user_name || 'Cardholder'
            const city = txn.city || 'India'
            const amt = Math.round(txn.amount || 0)
            announceVoice(`Security Alert: Fraud blocked for ${name} in ${city}. Amount: ${amt} Rupees.`)
          }
        } else if (txn.decision === 'FLAG') {
          playAlarmChime(false)
        }
      }
    }

    function onNewAlert(alert) {
      setAlerts((prev) => [alert, ...prev])
      if (voiceEnabled) {
        playAlarmChime(true)
      }
      // Show a toast
      const id = ++toastIdRef.current
      setToasts((prev) => [...prev, { ...alert, id }])
    }

    function onStatsUpdate(s) {
      setStats(s)
    }

    socket.on('new_transaction', onNewTxn)
    socket.on('new_alert',       onNewAlert)
    socket.on('stats_update',    onStatsUpdate)

    return () => {
      socket.off('new_transaction', onNewTxn)
      socket.off('new_alert',       onNewAlert)
      socket.off('stats_update',    onStatsUpdate)
    }
  }, [refreshStats, voiceEnabled])

  // ── Dismiss toast ─────────────────────────────────────────────────────────
  function dismissToast(id) {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  // ── Acknowledge alert ─────────────────────────────────────────────────────
  async function handleDismissAlert(id) {
    try {
      await acknowledgeAlert(id)
      setAlerts((prev) => prev.map((a) => a.id === id ? { ...a, acknowledged: true } : a))
    } catch {}
  }

  // ── Filter for Flagged tab ────────────────────────────────────────────────
  const flaggedTxns = transactions.filter((t) => t.decision === 'FLAG')

  return (
    <div className="app-layout">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="app-header">
        <span className="header-logo">🛡️</span>
        <h1>Fraud Detection Sandbox</h1>

        <nav className="tab-bar" role="navigation" aria-label="Main navigation">
          {['dashboard', 'map', 'rings', 'backtest', 'flagged', 'admin', 'ml', 'simulator'].map((tab) => (
            <button
              key={tab}
              className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
              id={`tab-${tab}`}
              aria-current={activeTab === tab ? 'page' : undefined}
            >
              {tab === 'dashboard' ? '📊 Dashboard' :
               tab === 'map'       ? '🗺️ Geo Map' :
               tab === 'rings'     ? '🕸️ Mule Rings' :
               tab === 'backtest'  ? '🧪 Backtester' :
               tab === 'flagged'   ? `🚩 Flagged (${flaggedTxns.length})` :
               tab === 'admin'     ? '👤 Admin' :
               tab === 'ml'        ? '🤖 ML Benchmark' :
                                    '⚙️ Simulator'}
            </button>
          ))}
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
          <button
            className={`btn ${voiceEnabled ? 'btn-ghost' : 'btn-ghost'}`}
            onClick={() => setVoiceEnabled((v) => !v)}
            id="voice-toggle-btn"
            aria-label="Toggle sound and voice announcer"
            title={voiceEnabled ? 'Mute audio siren & voice announcer' : 'Enable real-time audio siren & voice announcer'}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              color: voiceEnabled ? '#38bdf8' : 'var(--color-text-muted)',
              border: voiceEnabled ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid transparent',
              background: voiceEnabled ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
            }}
          >
            {voiceEnabled ? '🔊 Siren: ON' : '🔇 Siren: OFF'}
          </button>

          <button
            className="btn btn-ghost"
            onClick={async () => {
              if (!window.confirm('🗑️ Reset all transactions, alerts & network edges?\n\nUsers will be retained. You can then upload a fresh CSV.')) return
              try {
                const res = await resetDatabase()
                setTransactions([])
                setAlerts([])
                setToasts([])
                setSelectedTxn(null)
                setStats(null)
                refreshStats()
                setError(null)
                alert(`✅ ${res.message || 'Database reset complete!'}`)
              } catch (err) {
                setError('Reset failed: ' + err.message)
              }
            }}
            id="reset-btn"
            aria-label="Reset database"
            title="Clear all transactions, alerts & edges. Keeps users for fresh CSV upload."
            style={{
              color: '#f87171',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              background: 'rgba(239, 68, 68, 0.08)',
            }}
          >
            🗑️ Reset
          </button>

          <button
            className="btn btn-ghost"
            onClick={() => setShowSettings((v) => !v)}
            id="settings-toggle-btn"
            aria-label="Toggle rule settings"
          >
            ⚙ Settings
          </button>
        </div>
      </header>

      {/* ── Error banner ────────────────────────────────────────────────── */}
      {error && (
        <div role="alert" style={{
          background: 'var(--color-block-bg)', color: 'var(--color-block)',
          padding: '10px 24px', fontWeight: 600, fontSize: '0.85rem', textAlign: 'center',
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* ── Settings drawer ──────────────────────────────────────────────── */}
      {showSettings && <SettingsDrawer onClose={() => setShowSettings(false)} />}

      {/* ── Detail panel ─────────────────────────────────────────────────── */}
      {selectedTxn && (
        <BlockedDetail
          txn={selectedTxn}
          onClose={() => setSelectedTxn(null)}
          onActionComplete={() => {
            refreshStats()
            getTransactions({ limit: 50 }).then(setTransactions)
          }}
        />
      )}

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <main className="main-content">

        {/* ═══════════ DASHBOARD TAB ═══════════ */}
        {activeTab === 'dashboard' && (
          <>
            <SimulatorControls
              simStatus={simStatus}
              onStatusChange={(s) => setSimStatus((prev) => ({ ...prev, ...s }))}
              onError={setError}
            />
            <KpiCards stats={stats} />
            <SlaSpeedometer transactions={transactions} />
            <div className="charts-row">
              <DecisionDonut stats={stats} />
              <RuleBars stats={stats} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>
              <LiveFeed transactions={transactions} onSelectTxn={setSelectedTxn} />
              <Alerts alerts={alerts} onDismiss={handleDismissAlert} />
            </div>
          </>
        )}

        {/* ═══════════ GEO MAP TAB ═══════════ */}
        {activeTab === 'map' && (
          <>
            <SimulatorControls
              simStatus={simStatus}
              onStatusChange={(s) => setSimStatus((prev) => ({ ...prev, ...s }))}
              onError={setError}
            />
            <GeoMap transactions={transactions} />
          </>
        )}

        {/* ═══════════ RINGS TAB ═══════════ */}
        {activeTab === 'rings' && (
          <RingVisualizer />
        )}

        {/* ═══════════ BACKTESTER TAB ═══════════ */}
        {activeTab === 'backtest' && (
          <PolicyBacktester />
        )}

        {/* ═══════════ FLAGGED TAB ═══════════ */}
        {activeTab === 'flagged' && (
          <>
            <h2 style={{ marginBottom: 16, fontWeight: 700 }}>🚩 Flagged Review & Action Controls</h2>
            <AdminPanel initialView="flagged" />
          </>
        )}

        {/* ═══════════ ADMIN TAB ═══════════ */}
        {activeTab === 'admin' && (
          <>
            <h2 style={{ marginBottom: 16, fontWeight: 700 }}>👤 Admin Panel</h2>
            <AdminPanel />
          </>
        )}

        {/* ═══════════ ML TAB ═══════════ */}
        {activeTab === 'ml' && (
          <MlComparison />
        )}

        {/* ═══════════ SIMULATOR TAB ═══════════ */}
        {activeTab === 'simulator' && (
          <>
            <h2 style={{ marginBottom: 16, fontWeight: 700 }}>⚙️ Simulator Controls</h2>
            <SimulatorControls
              simStatus={simStatus}
              onStatusChange={(s) => setSimStatus((prev) => ({ ...prev, ...s }))}
              onError={setError}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
              <DecisionDonut stats={stats} />
              <RuleBars stats={stats} />
            </div>
            <div style={{ marginTop: 16 }}>
              <LiveFeed transactions={transactions.slice(0, 20)} onSelectTxn={setSelectedTxn} />
            </div>
          </>
        )}
      </main>

      {/* ── Toast container ─────────────────────────────────────────────── */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}
