/**
 * AdminPanel.jsx — Users table with freeze/unfreeze and flagged-txn overrides.
 * Tab: Admin / Flagged
 */
import { useState, useEffect, useCallback } from 'react'
import socket from '../socket'
import { getUsers, freezeUser, unfreezeUser, getTransactions, overrideTransaction } from '../api'

const fmt = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)

export default function AdminPanel({ initialView = 'users' }) {
  const [users, setUsers] = useState([])
  const [flagged, setFlagged] = useState([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [view, setView] = useState(initialView) // 'users' | 'flagged'

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (search) params.search = search
      if (filter) params.status = filter
      setUsers(await getUsers(params))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [search, filter])

  const loadFlagged = useCallback(async () => {
    setLoading(true)
    try {
      setFlagged(await getTransactions({ decision: 'FLAG', limit: 100 }))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  useEffect(() => {
    loadFlagged()
  }, [loadFlagged])

  // Automatically sync whenever a new transaction or CSV batch arrives via WebSocket
  useEffect(() => {
    function onNewTxn() {
      loadFlagged()
      loadUsers()
    }
    socket.on('new_transaction', onNewTxn)
    return () => {
      socket.off('new_transaction', onNewTxn)
    }
  }, [loadFlagged, loadUsers])

  async function handleFreeze(userId, frozen) {
    try {
      if (frozen) await unfreezeUser(userId)
      else await freezeUser(userId)
      await loadUsers()
      await loadFlagged()
    } catch (e) {
      alert(e.message)
    }
  }

  async function handleOverride(txnId, action) {
    try {
      await overrideTransaction(txnId, action)
      await loadFlagged()
    } catch (e) {
      alert(e.message)
    }
  }

  return (
    <div>
      {/* Sub-tab toggle */}
      <div className="admin-search" style={{ marginBottom: 0, display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className={`btn ${view === 'users' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setView('users')}
            id="admin-users-tab"
          >
            Users ({users.length})
          </button>
          <button
            className={`btn ${view === 'flagged' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setView('flagged')}
            id="admin-flagged-tab"
          >
            Flagged Transactions ({flagged.length})
          </button>
        </div>
        <button
          className="btn btn-ghost"
          onClick={() => {
            loadUsers()
            loadFlagged()
          }}
          title="Refresh table"
        >
          ↻ Refresh
        </button>
      </div>

      {view === 'users' ? (
        <>
          {/* Search & filter */}
          <div className="admin-search" style={{ marginTop: 16 }}>
            <input
              type="search"
              placeholder="Search by name or user ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search users"
              id="user-search-input"
            />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              aria-label="Filter by status"
              id="user-status-filter"
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="frozen">Frozen</option>
            </select>
            <button className="btn btn-ghost" onClick={loadUsers}>
              Search
            </button>
          </div>

          {/* Users table */}
          <div className="card" style={{ padding: 0, marginTop: 8 }}>
            <div className="feed-table-wrap">
              <table className="feed-table" aria-label="Users list">
                <thead>
                  <tr>
                    <th>User ID / Name</th>
                    <th>Home City</th>
                    <th>Avg Amount</th>
                    <th>Status</th>
                    <th>Txns</th>
                    <th>Blocked</th>
                    <th>Account Action</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && users.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: 24 }}>
                        Loading users…
                      </td>
                    </tr>
                  ) : users.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: 24 }}>
                        No users found.
                      </td>
                    </tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.user_id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{u.name}</div>
                          <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--color-text-muted)' }}>
                            {u.user_id}
                          </div>
                        </td>
                        <td>{u.home_city}</td>
                        <td style={{ fontWeight: 600 }}>{fmt(u.avg_amount)}</td>
                        <td>
                          <span className={`badge ${u.status === 'frozen' ? 'badge-block' : 'badge-approve'}`}>
                            {u.status}
                          </span>
                        </td>
                        <td>{u.total_txns}</td>
                        <td style={{ color: u.blocked_txns > 0 ? 'var(--color-block)' : 'inherit', fontWeight: u.blocked_txns > 0 ? 700 : 400 }}>
                          {u.blocked_txns}
                        </td>
                        <td>
                          <button
                            className={`btn ${u.status === 'frozen' ? 'btn-success' : 'btn-danger'}`}
                            style={{ fontSize: '0.75rem', padding: '5px 12px' }}
                            onClick={() => handleFreeze(u.user_id, u.status === 'frozen')}
                            id={`user-action-${u.user_id.slice(0, 8)}`}
                            aria-label={u.status === 'frozen' ? `Unfreeze ${u.name}` : `Freeze ${u.name}`}
                          >
                            {u.status === 'frozen' ? '✓ Unfreeze' : '❄️ Freeze Account'}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Flagged transactions list */
        <div className="card" style={{ padding: 0, marginTop: 16 }}>
          <div className="feed-table-wrap">
            <table className="feed-table" aria-label="Flagged transactions">
              <thead>
                <tr>
                  <th>Txn ID</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Location & Reasons</th>
                  <th>Risk Score</th>
                  <th>Decision Override</th>
                  <th>Account Freeze</th>
                </tr>
              </thead>
              <tbody>
                {flagged.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: 28, color: 'var(--color-text-muted)' }}>
                      ✅ No pending flagged transactions. All reviewed!
                    </td>
                  </tr>
                ) : (
                  flagged.map((t) => {
                    const reasonsStr = (t.reasons || []).map((r) => r.rule || r.detail).join(', ') || 'Rule Threshold Warning'
                    return (
                      <tr key={t.txn_id} className="row-flag">
                        <td style={{ fontFamily: 'monospace', fontSize: '0.78rem' }}>{t.txn_id.slice(0, 8)}…</td>
                        <td>
                          <div style={{ fontWeight: 600 }}>{t.user_name || t.user_id}</div>
                          <div style={{ fontSize: '0.72rem', fontFamily: 'monospace', color: 'var(--color-text-muted)' }}>
                            {t.user_id}
                          </div>
                        </td>
                        <td style={{ fontWeight: 700 }}>{fmt(t.amount)}</td>
                        <td>
                          <div>{t.city} • <span style={{ color: 'var(--color-text-muted)' }}>{t.merchant}</span></div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--color-flag)', marginTop: 2 }}>
                            ⚠️ {reasonsStr}
                          </div>
                        </td>
                        <td>
                          <span style={{ fontWeight: 700, color: 'var(--color-flag)', fontSize: '1rem' }}>
                            {t.risk_score}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>/100</span>
                        </td>
                        <td>
                          {t.overridden_by ? (
                            <span className={`badge ${t.overridden_by === 'APPROVE' ? 'badge-approve' : 'badge-block'}`}>
                              Overridden: {t.overridden_by}
                            </span>
                          ) : (
                            <div style={{ display: 'flex', gap: 6 }}>
                              <button
                                className="btn btn-success"
                                style={{ fontSize: '0.72rem', padding: '4px 10px' }}
                                onClick={() => handleOverride(t.txn_id, 'APPROVE')}
                                id={`approve-${t.txn_id.slice(0, 8)}`}
                                title="Approve transaction"
                              >
                                ✓ Approve
                              </button>
                              <button
                                className="btn btn-danger"
                                style={{ fontSize: '0.72rem', padding: '4px 10px' }}
                                onClick={() => handleOverride(t.txn_id, 'BLOCK')}
                                id={`block-${t.txn_id.slice(0, 8)}`}
                                title="Block transaction"
                              >
                                ✕ Block
                              </button>
                            </div>
                          )}
                        </td>
                        <td>
                          <button
                            className="btn btn-ghost"
                            style={{ fontSize: '0.72rem', padding: '4px 8px', color: 'var(--color-block)' }}
                            onClick={() => handleFreeze(t.user_id, false)}
                            id={`freeze-flagged-${t.txn_id.slice(0, 8)}`}
                            title="Freeze customer account"
                          >
                            ❄️ Freeze User
                          </button>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
