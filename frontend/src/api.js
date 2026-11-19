/**
 * api.js — Thin fetch wrapper for the Flask REST API.
 * All functions return the parsed JSON body or throw an Error.
 */

const BASE = '/api'

async function _fetch(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`)
  return json
}

// ── Transactions ──────────────────────────────────────────────────────────────
export const postTransaction = (data) =>
  _fetch('/transaction', { method: 'POST', body: JSON.stringify(data) })

export const getTransactions = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return _fetch(`/transactions${qs ? '?' + qs : ''}`)
}

export const overrideTransaction = (txnId, action) =>
  _fetch(`/transactions/${txnId}/override`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })

// ── Stats ────────────────────────────────────────────────────────────────────
export const getStats = () => _fetch('/stats')

// ── Users ────────────────────────────────────────────────────────────────────
export const getUsers = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return _fetch(`/users${qs ? '?' + qs : ''}`)
}

export const freezeUser   = (id) => _fetch(`/users/${id}/freeze`,   { method: 'POST' })
export const unfreezeUser = (id) => _fetch(`/users/${id}/unfreeze`, { method: 'POST' })

// ── Config ───────────────────────────────────────────────────────────────────
export const getConfig    = () => _fetch('/config')
export const updateConfig = (data) =>
  _fetch('/config', { method: 'PUT', body: JSON.stringify(data) })

// ── Simulator ────────────────────────────────────────────────────────────────
export const startSimulator  = () => _fetch('/simulator/start', { method: 'POST' })
export const stopSimulator   = () => _fetch('/simulator/stop',  { method: 'POST' })
export const setSimSpeed     = (min_delay, max_delay) =>
  _fetch('/simulator/speed', { method: 'PUT', body: JSON.stringify({ min_delay, max_delay }) })
export const injectPattern   = (pattern, user_id) =>
  _fetch('/simulator/inject', { method: 'POST', body: JSON.stringify({ pattern, user_id }) })
export const getSimStatus    = () => _fetch('/simulator/status')

// ── Alerts ───────────────────────────────────────────────────────────────────
export const getAlerts           = () => _fetch('/simulator/alerts')
export const acknowledgeAlert    = (id) =>
  _fetch(`/simulator/alerts/${id}/acknowledge`, { method: 'POST' })

// ── ML Anomaly Detection ─────────────────────────────────────────────────────
export const getMlComparison     = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return _fetch(`/ml/compare${qs ? '?' + qs : ''}`)
}

export const retrainMl           = () => _fetch('/ml/retrain', { method: 'POST' })

// ── ML Supervised / Metrics ───────────────────────────────────────────────────
export const getMlMetrics    = ()         => fetch(`${BASE}/ml/metrics`).then(r => r.json())
export const retrainRf       = ()         => fetch(`${BASE}/ml/retrain-supervised`, {method:'POST'}).then(r => r.json())
export const getRfCompare    = ()         => fetch(`${BASE}/ml/rf-compare`).then(r => r.json())

// ── Notifications ────────────────────────────────────────────────────────────
export const getNotifyLog    = ()         => fetch(`${BASE}/notify/log`).then(r => r.json())
export const clearNotifyLog  = ()         => fetch(`${BASE}/notify/log`, {method:'DELETE'}).then(r => r.json())
export const sendTestNotify  = (type, user_id) => fetch(`${BASE}/notify/test`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type, user_id})}).then(r => r.json())

// ── Replay ───────────────────────────────────────────────────────────────────
export const getReplayStatus = ()         => fetch(`${BASE}/replay/status`).then(r => r.json())
export const startReplay     = (file)     => fetch(`${BASE}/replay/start`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({file})}).then(r => r.json())
export const stopReplay      = ()         => fetch(`${BASE}/replay/stop`, {method:'POST'}).then(r => r.json())
export const getRings        = ()         => fetch(`${BASE}/rings`).then(r => r.json())

// ── Export ───────────────────────────────────────────────────────────────────
export const exportTxnsCsv   = ()         => { window.open(`${BASE}/export/transactions.csv`, '_blank') }
export const exportFlaggedCsv= ()         => { window.open(`${BASE}/export/flagged.csv`, '_blank') }

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authLogin       = (u, p)     => fetch(`${BASE}/auth/login`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u, password:p})}).then(r => r.json())
export const authLogout      = ()         => fetch(`${BASE}/auth/logout`, {method:'POST'}).then(r => r.json())
export const authMe          = ()         => fetch(`${BASE}/auth/me`).then(r => r.json())

export const uploadCsv = async (file, stream = true) => {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`/api/transactions/upload-csv?stream=${stream}`, {
    method: 'POST',
    body: formData,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`)
  return json
}

// ── What-If Policy Backtester ────────────────────────────────────────────────
export const runBacktest = (policyData = {}) =>
  _fetch('/backtest', { method: 'POST', body: JSON.stringify(policyData) })

