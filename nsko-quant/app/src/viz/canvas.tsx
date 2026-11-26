import { useEffect, useRef } from 'react'
import { reducedMotion } from '../tokens'

// A DPR-aware canvas that redraws every frame (or once when the user prefers reduced motion).
export function Canvas({ draw, style, className }: { draw: (c: CanvasRenderingContext2D, w: number, h: number, t: number, dt: number) => void; style?: any; className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null); const fn = useRef(draw); fn.current = draw
  useEffect(() => {
    const cv = ref.current!; const ctx = cv.getContext('2d')!; let raf = 0, last = performance.now(), w = 0, h = 0
    const size = () => { const r = cv.getBoundingClientRect(); const d = Math.min(2, devicePixelRatio || 1); w = r.width; h = r.height; cv.width = w * d; cv.height = h * d; ctx.setTransform(d, 0, 0, d, 0, 0) }
    size(); const ro = new ResizeObserver(size); ro.observe(cv)
    const loop = (now: number) => { const dt = Math.min(.05, (now - last) / 1000); last = now; fn.current(ctx, w, h, now / 1000, dt); if (!reducedMotion()) raf = requestAnimationFrame(loop) }
    raf = requestAnimationFrame(loop); return () => { cancelAnimationFrame(raf); ro.disconnect() }
  }, [])
  return <canvas ref={ref} className={className} style={{ width: '100%', height: '100%', display: 'block', ...style }} />
}

export function Spark({ data, color = '#78D880', w = 80, h = 22, fill = false }: { data: number[]; color?: string; w?: number; h?: number; fill?: boolean }) {
  if (data.length < 2) return <svg width={w} height={h} />
  const mn = Math.min(...data), mx = Math.max(...data), r = mx - mn || 1
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - 2 - ((v - mn) / r) * (h - 4)}`).join(' ')
  return <svg width={w} height={h} style={{ display: 'block' }}>{fill && <polygon points={`0,${h} ${pts} ${w},${h}`} fill={color} opacity={.12} />}<polyline points={pts} fill="none" stroke={color} strokeWidth={1.2} /></svg>
}

// seeded walk for static demo sparklines
export function walk(seed: number, n = 40, drift = .02) { let a = seed, v = 0; const out: number[] = []; for (let i = 0; i < n; i++) { a = (a * 9301 + 49297) % 233280; v += (a / 233280 - .5 + drift); out.push(v) } return out }
