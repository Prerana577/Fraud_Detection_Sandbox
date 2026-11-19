import { useState, useEffect } from 'react'
import { getRings, freezeUser } from '../api'

export default function RingVisualizer() {
  const [data, setData] = useState({ rings: [], shared_locations: [], graph: { nodes: [], edges: [] } })
  const [loading, setLoading] = useState(true)
  const [selectedRing, setSelectedRing] = useState(null)
  const [actionMsg, setActionMsg] = useState(null)

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await getRings()
      setData(res)
      if (res.rings && res.rings.length > 0) {
        setSelectedRing(res.rings[0])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleFreezeRingUsers = async (userIds) => {
    try {
      for (const id of userIds) {
        await freezeUser(id)
      }
      setActionMsg(`✓ Successfully frozen ${userIds.length} accounts in this syndicate ring!`)
      setTimeout(() => setActionMsg(null), 4000)
      loadData()
    } catch (e) {
      setActionMsg(`Error freezing accounts: ${e.message}`)
    }
  }

  const rings = data.rings || []
  const sharedLocs = data.shared_locations || []
  const nodes = data.graph?.nodes || []
  const edges = data.graph?.edges || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>🕸️ Syndicate & Mule Ring Link Analysis</h2>
          <p style={{ fontSize: '0.85rem', color: '#888', marginTop: 4 }}>
            Detects collusion where multiple synthetic accounts share physical POS terminals or virtual merchants in tight temporal windows.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={loadData} disabled={loading}>
          {loading ? 'Analyzing…' : '🔄 Refresh Link Analysis'}
        </button>
      </div>

      {actionMsg && (
        <div style={{ padding: '10px 16px', background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', borderRadius: 8, fontWeight: 600, fontSize: '0.85rem' }}>
          {actionMsg}
        </div>
      )}

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 16 }}>
        {/* Interactive SVG Network Graph */}
        <div style={{
          background: 'var(--color-card)',
          borderRadius: 12,
          border: '1px solid var(--color-border)',
          padding: 16,
          height: '540px',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#aaa' }}>
              COLLUSION TOPOLOGY ({nodes.length} entities • {edges.length} transactions)
            </span>
            <div style={{ display: 'flex', gap: 12, fontSize: '0.75rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6' }} /> User Account
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: '#f59e0b' }} /> Merchant / POS Terminal
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 12, height: 2, background: '#ef4444' }} /> High-Risk Link
              </span>
            </div>
          </div>

          <div style={{ flex: 1, position: 'relative', overflow: 'hidden', background: '#0a0f1d', borderRadius: 8 }}>
            <svg width="100%" height="100%" viewBox="0 0 700 460" preserveAspectRatio="xMidYMid meet">
              <defs>
                <radialGradient id="ringGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                </radialGradient>
              </defs>

              {/* Background Glow for Suspected Rings */}
              {rings.map((ring, idx) => {
                const cx = 150 + (idx % 3) * 180
                const cy = 140 + Math.floor(idx / 3) * 160
                return (
                  <circle
                    key={idx}
                    cx={cx}
                    cy={cy}
                    r="85"
                    fill="url(#ringGlow)"
                    stroke="#ef4444"
                    strokeWidth="1.5"
                    strokeDasharray="4,4"
                  />
                )
              })}

              {/* Connecting Edges */}
              {edges.slice(0, 50).map((edge, idx) => {
                // Layout nodes mathematically around ring clusters
                const uIdx = nodes.findIndex((n) => n.id === edge.source)
                const mIdx = nodes.findIndex((n) => n.id === edge.target)
                const x1 = 60 + ((uIdx * 47) % 580)
                const y1 = 60 + ((uIdx * 71) % 340)
                const x2 = 120 + ((mIdx * 89) % 480)
                const y2 = 80 + ((mIdx * 53) % 300)

                const isFraud = edge.decision === 'BLOCK' || edge.risk_score >= 60

                return (
                  <line
                    key={idx}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={isFraud ? '#ef4444' : '#334155'}
                    strokeWidth={isFraud ? 2 : 1}
                    opacity={isFraud ? 0.8 : 0.4}
                  />
                )
              })}

              {/* User and Merchant Nodes */}
              {nodes.slice(0, 45).map((node, idx) => {
                const isUser = node.type === 'user'
                const x = isUser ? 60 + ((idx * 47) % 580) : 120 + ((idx * 89) % 480)
                const y = isUser ? 60 + ((idx * 71) % 340) : 80 + ((idx * 53) % 300)
                const isFrozen = node.status === 'frozen'

                return (
                  <g key={idx} transform={`translate(${x}, ${y})`}>
                    {isUser ? (
                      <circle
                        r="12"
                        fill={isFrozen ? '#ef4444' : '#3b82f6'}
                        stroke="#fff"
                        strokeWidth="1.5"
                      />
                    ) : (
                      <rect
                        x="-10"
                        y="-10"
                        width="20"
                        height="20"
                        rx="3"
                        fill="#f59e0b"
                        stroke="#fff"
                        strokeWidth="1.5"
                      />
                    )}
                    <text
                      y={isUser ? 24 : 26}
                      textAnchor="middle"
                      fill="#e2e8f0"
                      fontSize="9"
                      fontWeight="bold"
                    >
                      {node.label.length > 10 ? `${node.label.slice(0, 9)}…` : node.label}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        </div>

        {/* Ring Details Panel */}
        <div style={{
          background: 'var(--color-card)',
          borderRadius: 12,
          border: '1px solid var(--color-border)',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          overflowY: 'auto',
          maxHeight: '540px',
        }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f87171' }}>
              🚨 Detected Mule Rings ({rings.length})
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#888', marginTop: 4 }}>
              Accounts colluding at the same merchant within a 10-minute window.
            </p>
          </div>

          {rings.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 8px', color: '#666', fontSize: '0.85rem' }}>
              ✓ No active multi-account rings detected in current transaction window.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {rings.map((ring, idx) => (
                <div
                  key={idx}
                  onClick={() => setSelectedRing(ring)}
                  style={{
                    padding: 12,
                    borderRadius: 8,
                    background: selectedRing?.ring_id === ring.ring_id ? 'rgba(239, 68, 68, 0.2)' : 'var(--color-bg)',
                    border: `1px solid ${selectedRing?.ring_id === ring.ring_id ? '#ef4444' : 'var(--color-border)'}`,
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, color: '#f87171' }}>
                    <span>Ring #{ring.ring_id + 1}</span>
                    <span>{ring.txn_count} Txns</span>
                  </div>
                  <div style={{ marginTop: 4, fontWeight: 600 }}>🏪 {ring.merchant} ({ring.city})</div>
                  <div style={{ color: '#aaa', marginTop: 4, fontSize: '0.75rem' }}>
                    Colluding Accounts: {ring.user_ids?.length || 0}
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 6 }}>
                    {ring.user_ids?.map((uid, uidx) => (
                      <span key={uidx} style={{ background: '#1e293b', padding: '2px 6px', borderRadius: 4, fontSize: '0.7rem' }}>
                        {uid}
                      </span>
                    ))}
                  </div>

                  <button
                    className="btn btn-danger"
                    style={{ width: '100%', marginTop: 8, padding: '4px 8px', fontSize: '0.75rem' }}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleFreezeRingUsers(ring.user_ids)
                    }}
                  >
                    🔒 Freeze Ring Accounts ({ring.user_ids?.length})
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Shared Location Clusters */}
          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 12 }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f59e0b', marginBottom: 8 }}>
              📍 Concurrent City Surges ({sharedLocs.length})
            </h4>
            {sharedLocs.slice(0, 4).map((s, idx) => (
              <div key={idx} style={{ padding: '6px 8px', background: 'var(--color-bg)', borderRadius: 6, fontSize: '0.75rem', marginBottom: 6 }}>
                <strong>{s.city}:</strong> {s.user_ids?.length} accounts within 2 mins
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
