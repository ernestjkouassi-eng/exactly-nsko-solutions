// NSKO QUANT design tokens. Every colour in the app comes from here.
export const T = {
  bg: '#08080F', panel: '#0C0D14', line: '#1A1C26', textHi: '#E8E8EC', textLo: '#5A5F6E',
  orange: '#E8541A', green: '#78D880', amber: '#E8A850', red: '#E04858', cyan: '#20E0F0',
  magenta: '#F01848', pink: '#F8A0C0', blue: '#5A8CFF',
  ease: 'cubic-bezier(0.2,0.8,0.2,1)',
} as const
export const VERB_COL: Record<string, string> = {
  SEARCH: T.cyan, READ: T.textHi, SAVE: T.green, REJECT: T.red, TERM: T.amber, SUMMARISE: T.blue,
  PAUSE: T.textLo, BUDGET: T.amber, TRADE: T.orange, TEST: T.textHi, RISK: T.amber,
}
export const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
