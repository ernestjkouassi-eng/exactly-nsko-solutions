import { useMemo, useState, type FormEvent } from 'react'
import { Wordmark } from '../shell/Shell'
import { RiskWarning } from '../pages/Money'
import { useAcct, signUp, logIn, sendReset, setNewPassword, PRODUCT_URL, type Experience } from './account'

// Account gate for the web demo: create an account or log in, then the desk opens on demo data.
const CODES = 'GB IE US CA AU NZ ZA NG GH KE CI SN CM FR DE ES IT PT NL BE LU CH AT DK SE NO FI IS PL CZ SK HU RO BG GR CY MT HR SI EE LV LT UA TR IL AE SA QA KW BH OM JO EG MA TN DZ IN PK BD LK NP SG MY ID TH VN PH HK TW JP KR CN MX BR AR CL CO PE UY EC VE JM TT BB BS'.split(' ')
const EXP: [Experience, string][] = [['new', 'New'], ['some', 'Some'], ['experienced', 'Experienced']]
type View = 'signup' | 'login' | 'forgot' | 'sent' | 'reset-sent'

export default function Gate() {
  const status = useAcct(s => s.status), urlNote = useAcct(s => s.urlNote)
  const [view, setView] = useState<View>('signup')
  const [f, setF] = useState({ name: '', email: '', password: '', country: '', experience: '' as Experience | '', marketing: false, agree: false })
  const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  const countries = useMemo(() => { let dn: Intl.DisplayNames | null = null; try { dn = new Intl.DisplayNames(['en-GB'], { type: 'region' }) } catch { /* old browser */ }
    const all = CODES.map(c => [c, dn?.of(c) || c] as const); return [all[0], ...all.slice(1).sort((a, b) => a[1].localeCompare(b[1])), ['XX', 'Other'] as const] }, [])
  const up = (k: keyof typeof f, v: any) => { setF(x => ({ ...x, [k]: v })); setErr('') }
  const go = (v: View) => { setView(v); setErr(''); setF(x => ({ ...x, password: '' })) }
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(f.email.trim())

  const submit = async (e: FormEvent) => {
    e.preventDefault(); if (busy) return
    if (view === 'signup') {
      const miss = !f.name.trim() ? 'Please enter your name.' : !emailOk ? 'Please enter a valid email address.' : f.password.length < 10 ? 'Your password needs at least 10 characters.'
        : !f.country ? 'Please choose your country.' : !f.experience ? 'Please choose your trading experience.' : !f.agree ? 'Please tick the box to agree to the demo terms and privacy notice.' : ''
      if (miss) return setErr(miss)
      setBusy(true); const r = await signUp({ name: f.name, email: f.email, password: f.password, country: countries.find(c => c[0] === f.country)?.[1] || f.country, experience: f.experience as Experience, marketing: f.marketing }); setBusy(false)
      if (!r.ok) return setErr(r.error)
      if (r.confirm) go('sent')
    } else if (view === 'login') {
      if (!emailOk || !f.password) return setErr('Please enter your email and password.')
      setBusy(true); const r = await logIn(f.email, f.password); setBusy(false)
      if (!r.ok) return setErr(r.error)
    } else if (view === 'forgot') {
      if (!emailOk) return setErr('Please enter the email you signed up with.')
      setBusy(true); const r = await sendReset(f.email); setBusy(false)
      if (!r.ok) return setErr(r.error)
      go('reset-sent')
    }
  }

  if (status === 'loading') return <div className="gate"><div className="lbl" style={{ margin: 'auto' }}><span className="dot pulse" /> LOADING</div></div>
  if (status === 'recovery') return <Recovery />

  const tabs = view === 'signup' || view === 'login'
  return <div className="gate" data-testid="gate">
    <div className="gate-card panel">
      <Head />
      {urlNote && <div className="gate-note">{urlNote}</div>}
      {tabs && <div className="gate-tabs" role="tablist">
        {([['signup', 'Create account'], ['login', 'Log in']] as const).map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? 'on' : ''} onClick={() => go(k)}>{l}</button>)}
      </div>}

      {view === 'sent' ? <Done title="CHECK YOUR EMAIL" body={<>We sent a confirmation link to <b>{f.email.trim()}</b>. Open it and the demo opens. No email after a few minutes? Check your spam folder.</>} back={() => go('login')} />
      : view === 'reset-sent' ? <Done title="RESET LINK SENT" body={<>If an account exists for <b>{f.email.trim()}</b>, an email with a link to set a new password is on its way.</>} back={() => go('login')} />
      : <form onSubmit={submit} noValidate className="gate-form">
        {view === 'forgot' && <div className="lbl" style={{ color: 'var(--hi)' }}>RESET YOUR PASSWORD</div>}
        {view === 'signup' && <Field l="Name"><input value={f.name} onChange={e => up('name', e.target.value)} autoComplete="name" maxLength={120} /></Field>}
        <Field l="Email"><input type="email" value={f.email} onChange={e => up('email', e.target.value)} autoComplete="email" inputMode="email" /></Field>
        {view !== 'forgot' && <Field l="Password" hint={view === 'signup' ? 'At least 10 characters' : undefined}>
          <input type="password" value={f.password} onChange={e => up('password', e.target.value)} autoComplete={view === 'signup' ? 'new-password' : 'current-password'} minLength={view === 'signup' ? 10 : undefined} /></Field>}
        {view === 'signup' && <>
          <Field l="Country"><select value={f.country} onChange={e => up('country', e.target.value)}><option value="">Choose…</option>{countries.map(([c, n]) => <option key={c} value={c}>{n}</option>)}</select></Field>
          <div><div className="lbl" style={{ marginBottom: 6 }}>Trading experience</div>
            <div className="gate-seg" role="radiogroup">{EXP.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={f.experience === k} className={f.experience === k ? 'on' : ''} onClick={() => up('experience', k)}>{l}</button>)}</div></div>
          <label className="gate-check"><input type="checkbox" checked={f.marketing} onChange={e => up('marketing', e.target.checked)} /><span>Send me NSKO QUANT news</span></label>
          <label className="gate-check"><input type="checkbox" checked={f.agree} onChange={e => up('agree', e.target.checked)} /><span>I agree to the <a href="#demo-terms" onClick={e => { e.preventDefault(); document.getElementById('demo-terms')?.toggleAttribute('open') }}>demo terms</a> and the <a href="/privacy" target="_blank" rel="noopener">privacy notice</a>.</span></label>
          <details id="demo-terms" className="gate-terms"><summary>Demo terms</summary>
            <p>This is a demo on made-up data. There is no real trading, no broker connection and no money involved. Nothing on the desk is financial advice. We keep your name, email, country, experience and news choice to run your demo account; ask us to delete it at any time at hello@nskosolutions.co.uk.</p></details>
        </>}
        {err && <div className="gate-err" role="alert" data-testid="gate-error">{err}</div>}
        <button className="primary" type="submit" disabled={busy} style={{ width: '100%', padding: 11 }}>{busy ? 'Please wait…' : view === 'signup' ? 'Create account and open the demo' : view === 'login' ? 'Log in' : 'Send reset link'}</button>
        {view === 'login' && <button type="button" className="gate-link" onClick={() => go('forgot')}>Forgot password?</button>}
        {view === 'forgot' && <button type="button" className="gate-link" onClick={() => go('login')}>‹ Back to log in</button>}
      </form>}
      <Foot />
    </div>
  </div>
}

function Recovery() {
  const [pw, setPw] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  const save = async (e: FormEvent) => { e.preventDefault(); if (pw.length < 10) return setErr('Your password needs at least 10 characters.'); setBusy(true); const r = await setNewPassword(pw); setBusy(false); if (!r.ok) setErr(r.error) }
  return <div className="gate" data-testid="gate"><div className="gate-card panel"><Head />
    <form onSubmit={save} noValidate className="gate-form"><div className="lbl" style={{ color: 'var(--hi)' }}>CHOOSE A NEW PASSWORD</div>
      <Field l="New password" hint="At least 10 characters"><input type="password" value={pw} onChange={e => { setPw(e.target.value); setErr('') }} autoComplete="new-password" autoFocus /></Field>
      {err && <div className="gate-err" role="alert">{err}</div>}
      <button className="primary" type="submit" disabled={busy} style={{ width: '100%', padding: 11 }}>{busy ? 'Saving…' : 'Save and open the demo'}</button></form>
    <Foot /></div></div>
}

const Head = () => <div style={{ textAlign: 'center', marginBottom: 18 }}>
  <Wordmark size={24} /><div className="lo" style={{ marginTop: 6, fontSize: 11 }}>by NSKO Solutions</div>
  <div className="gate-h">Try the live demo</div>
  <div className="lbl" style={{ marginTop: 6 }}><span className="a">●</span> Demo data only · no real trading · no money</div>
</div>
const Field = ({ l, hint, children }: { l: string; hint?: string; children: any }) =>
  <label className="gate-field"><span className="lbl">{l}{hint && <span className="gate-hint"> · {hint}</span>}</span>{children}</label>
const Done = ({ title, body, back }: { title: string; body: any; back: () => void }) => <div className="gate-form" data-testid="gate-done">
  <div className="lbl g">{title}</div><div style={{ lineHeight: 1.6, color: '#B8BCC8' }}>{body}</div>
  <button type="button" onClick={back} style={{ width: '100%', padding: 10 }}>Back to log in</button></div>
const Foot = () => <div className="gate-foot">
  <a className="gate-dl" href={PRODUCT_URL}>Download the app</a>
  <RiskWarning />
</div>
