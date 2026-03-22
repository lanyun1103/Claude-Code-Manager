// Shared tag color definitions used across all components
// Color key → Tailwind classes mapping

export const TAG_COLOR_OPTIONS = [
  { key: 'indigo',  label: 'Indigo',  bg: 'bg-indigo-500/20',  text: 'text-indigo-300',  border: 'border-indigo-500/30',  dot: 'bg-indigo-400' },
  { key: 'sky',     label: 'Sky',     bg: 'bg-sky-500/20',     text: 'text-sky-300',     border: 'border-sky-500/30',     dot: 'bg-sky-400' },
  { key: 'emerald', label: 'Emerald', bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  { key: 'amber',   label: 'Amber',   bg: 'bg-amber-500/20',   text: 'text-amber-300',   border: 'border-amber-500/30',   dot: 'bg-amber-400' },
  { key: 'rose',    label: 'Rose',    bg: 'bg-rose-500/20',    text: 'text-rose-300',    border: 'border-rose-500/30',    dot: 'bg-rose-400' },
  { key: 'violet',  label: 'Violet',  bg: 'bg-violet-500/20',  text: 'text-violet-300',  border: 'border-violet-500/30',  dot: 'bg-violet-400' },
  { key: 'cyan',    label: 'Cyan',    bg: 'bg-cyan-500/20',    text: 'text-cyan-300',    border: 'border-cyan-500/30',    dot: 'bg-cyan-400' },
  { key: 'orange',  label: 'Orange',  bg: 'bg-orange-500/20',  text: 'text-orange-300',  border: 'border-orange-500/30',  dot: 'bg-orange-400' },
  { key: 'pink',    label: 'Pink',    bg: 'bg-pink-500/20',    text: 'text-pink-300',    border: 'border-pink-500/30',    dot: 'bg-pink-400' },
  { key: 'teal',    label: 'Teal',    bg: 'bg-teal-500/20',    text: 'text-teal-300',    border: 'border-teal-500/30',    dot: 'bg-teal-400' },
] as const;

export type TagColorKey = typeof TAG_COLOR_OPTIONS[number]['key'];

const COLOR_MAP = Object.fromEntries(TAG_COLOR_OPTIONS.map((c) => [c.key, c]));

// Fallback: deterministic hash for tags without stored color
function hashColor(tag: string): typeof TAG_COLOR_OPTIONS[number] {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) hash = (hash * 31 + tag.charCodeAt(i)) & 0xffff;
  return TAG_COLOR_OPTIONS[hash % TAG_COLOR_OPTIONS.length];
}

/**
 * Resolve a tag's color classes.
 * @param tagName - the tag string
 * @param colorKey - stored color key from Tag table (if available)
 */
export function resolveTagColor(tagName: string, colorKey?: string) {
  if (colorKey && COLOR_MAP[colorKey]) return COLOR_MAP[colorKey];
  return hashColor(tagName);
}
