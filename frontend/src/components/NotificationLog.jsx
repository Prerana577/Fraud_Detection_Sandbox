import { useState, useEffect } from 'react'
import { getNotifyLog, clearNotifyLog, sendTestNotify } from '../api'

export default function NotificationLog() {
  const [log, setLog] = useState([])
  const [testType, setTestType] = useState('fraud_alert')
  const [testUserId, setTestUserId] = useState('')
  const [status, setStatus] = useState('')

  const refresh = () => getNotifyLog().then(d => setLog(d.log || []))
  useEffect(() => { refresh(); const id = setInterval(refresh, 5000); return () => clearInterval(id) }, [])

  const handleClear = () => clearNotifyLog().then(refresh)
  const handleTest = () => sendTestNotify(testType, testUserId).then(() => { setStatus('Sent!'); refresh() }).catch(() => setStatus('Error'))

  const typeIcon = t => t === 'fraud_alert' ? '🚨' : t === 'account_frozen' ? '🔒' : '📱'

  return (
    <div>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12}}>
        <h2 style={{fontWeight:700}}>🔔 Notification Log</h2>
        <button className="btn btn-ghost" onClick={handleClear}>Clear Log</button>
      </div>
      <div style={{background:'var(--color-card)', borderRadius:8, padding:16, marginBottom:16}}>
        <h3 style={{marginBottom:8, fontSize:'0.9rem'}}>Send Test Notification</h3>
        <div style={{display:'flex', gap:8, alignItems:'center', flexWrap:'wrap'}}>
          <select value={testType} onChange={e => setTestType(e.target.value)} style={{padding:'4px 8px', borderRadius:4, background:'var(--color-bg)', color:'var(--color-text)', border:'1px solid #444'}}>
            <option value="fraud_alert">🚨 Fraud Alert</option>
            <option value="account_frozen">🔒 Account Frozen</option>
            <option value="otp_challenge">📱 OTP Challenge</option>
          </select>
          <input value={testUserId} onChange={e => setTestUserId(e.target.value)} placeholder="User ID" style={{padding:'4px 8px', borderRadius:4, background:'var(--color-bg)', color:'var(--color-text)', border:'1px solid #444', width:220}} />
          <button className="btn btn-primary" onClick={handleTest}>Send</button>
          {status && <span style={{fontSize:'0.8rem', color:'#4ade80'}}>{status}</span>}
        </div>
      </div>
      <div style={{display:'flex', flexDirection:'column', gap:8}}>
        {log.length === 0 && <p style={{color:'#666', textAlign:'center'}}>No notifications yet</p>}
        {log.map((entry, i) => (
          <div key={i} style={{background:'var(--color-card)', borderRadius:8, padding:'10px 14px', borderLeft:`3px solid ${entry.type==='fraud_alert'?'#ef4444':entry.type==='account_frozen'?'#f59e0b':'#3b82f6'}`}}>
            <div style={{display:'flex', justifyContent:'space-between'}}>
              <span>{typeIcon(entry.type)} {entry.message}</span>
              <span style={{fontSize:'0.75rem', color:'#888'}}>{new Date(entry.timestamp).toLocaleTimeString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
