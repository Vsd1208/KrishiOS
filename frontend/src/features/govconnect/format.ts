import type { Severity, Span } from '@/services/api/govconnect';

export const SEVERITY_STYLE: Record<Severity, string> = {
  CRITICAL: 'bg-danger-600 text-white',
  HIGH: 'bg-orange-500 text-white',
  MEDIUM: 'bg-amber-300 text-amber-950',
  LOW: 'bg-surface-raised text-text-secondary border border-border',
};

export function formatDate(iso: string | null | undefined, lang: string): string {
  if (!iso) return '—';
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-IN' : `${lang}-IN`, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso));
}

/** Split the official text into plain and highlighted pieces (one field per span). Spans that
 * overlap or no longer match the text are skipped. */
export function highlightSegments(body: string, provenance: Record<string, Span[]>) {
  const spans = Object.entries(provenance)
    .filter(([field]) => field !== 'title' && field !== 'authority_level')
    .flatMap(([field, list]) => list.map((s) => ({ ...s, field })))
    .sort((a, b) => a.start - b.start || b.end - a.end);
  const out: { text: string; field?: string }[] = [];
  let pos = 0;
  for (const s of spans) {
    if (s.start < pos || s.end > body.length || body.slice(s.start, s.end) !== s.text) continue;
    if (s.start > pos) out.push({ text: body.slice(pos, s.start) });
    out.push({ text: s.text, field: s.field });
    pos = s.end;
  }
  if (pos < body.length) out.push({ text: body.slice(pos) });
  return out;
}
