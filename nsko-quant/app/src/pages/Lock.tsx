import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useS } from '../store'
import { Wordmark, SourceChips } from '../shell/Shell'
import { login } from '../api'
import { afterLogin, selectDemo, selectEngine } from '../source'

// Lock screen: in engine mode the desk only shows after login (password, then PIN or authenticator code if enabled).
export default function Lock() {
  const conn = useS(s => s.conn)
  const [email, setEmail] = useState(() => { try { return localStorage.getItem('nq_email') || '' } catch { return '' } })
  const [pw, setPw] = useState(''); const [code, setCode] = useState(''); const [need, setNeed] = useState<'pin' | 'totp' | null>(null)
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [fails, setFails] = useState(0)
  const codeRef = useRef<HTMLInputElement>(null)
  useEffect(() => { if (need) codeRef.current?.focus() }, [need])
  const submit = async (e?: FormEvent) => {
    e?.preventDefault(); if (busy || !pw) return
    setBusy(true); setErr('')
    const r = await login({ email: email || undefined, password: pw, ...(need === 'pin' ? { pin: code } : need === 'totp' ? { totp: code } : {}) })
    setBusy(false)
    const second = r.data?.need || (r.code === 'totp_required' ? 'totp' : r.code === 'pin_required' ? 'pin' : null)
    if (!r.ok && second && !need) { setNeed(second); setCode(''); return }
    if (r.ok && r.data.token) { try { if (email) localStorage.setItem('nq_email', email) } catch { /* ignore */ } setPw(''); setCode(''); afterLogin({ token: r.data.token, name: r.data.name, email: r.data.email || email }); return }
    if (r.ok && r.data.need) { setNeed(r.data.need); setCode(''); return }
    setFails(f => f + 1); setCode(''); setErr(r.error || 'Wrong password')
  }
  const step = need ? 2 : 1
  return <div style={{ position: 'fixed', inset: 0, zIndex: 110, background: 'radial-gradient(circle at 50% 28%, #14141E, #08080F 62%)', display: 'grid', placeItems: 'center' }}>
    <div style={{ position: 'absolute', top: 16, right: 18 }} className="row"><SourceChips /></div>
    <form onSubmit={submit} className="panel" style={{ width: 420, padding: 28 }}>
      <div style={{ textAlign: 'center', marginBottom: 22 }}><Wordmark size={24} /><div className="lo" style={{ marginTop: 6, fontSize: 11 }}>by NSKO Solutions</div></div>
      <div className="row" style={{ gap: 4, marginBottom: 14 }}>{[1, 2].map(i => <i key={i} style={{ flex: 1, height: 2, background: i <= step ? 'var(--orange)' : 'var(--line)' }} />)}</div>
      <div className="lbl" style={{ marginBottom: 12 }}>{need ? `STEP 2 OF 2 · ${need === 'pin' ? '6-DIGIT PIN' : 'AUTHENTICATOR CODE'}` : 'UNLOCK THE DESK'}</div>
      {!need ? <div className="grid" style={{ gap: 9 }}>
        <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" />
        <input type="password" placeholder="Password" value={pw} onChange={e => setPw(e.target.value)} autoComplete="current-password" autoFocus />
      </div> : <div>
        <input ref={codeRef} inputMode="numeric" maxLength={6} value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ''))} placeholder="••••••" className="num"
          type={need === 'pin' ? 'password' : 'text'} style={{ width: '100%', textAlign: 'center', fontSize: 24, letterSpacing: '.5em', padding: '12px 0' }} />
        <div className="lo" style={{ fontSize: 11, marginTop: 8 }}>{need === 'pin' ? 'The PIN you chose when you set up this desk.' : 'The 6-digit code from your authenticator app.'}</div>
      </div>}
      {err && <div className="r mono" style={{ fontSize: 11, marginTop: 10 }}>{err}{fails >= 3 ? ' · lost it? Use your recovery code in the engine\'s reset tool.' : ''}</div>}
      <button className="primary" type="submit" disabled={busy || !pw || (!!need && code.length !== 6)} style={{ width: '100%', marginTop: 16, padding: 10 }}>{busy ? 'Checking…' : need ? 'Unlock' : 'Continue'}</button>
      <div className="row" style={{ justifyContent: 'space-between', marginTop: 14 }}>
        {need ? <button type="button" onClick={() => { setNeed(null); setCode('') }} style={{ fontSize: 11, padding: '3px 8px' }}>‹ Back</button> : <span className="lo mono" style={{ fontSize: 10 }}>ENGINE · 127.0.0.1:8787 · {conn.toUpperCase()}</span>}
        <button type="button" onClick={() => selectDemo()} style={{ fontSize: 11, padding: '3px 8px' }}>Use demo data instead</button></div>
      <div className="lo" style={{ fontSize: 10, marginTop: 14, lineHeight: 1.5 }}>The engine keeps trading while the desk is locked. Your login is checked by the engine on this computer; nothing is sent to NSKO.</div>
      {conn === 'offline' && <button type="button" onClick={() => selectEngine(false)} style={{ marginTop: 10, width: '100%' }}>Engine not answering · retry</button>}
    </form>
  </div>
}
