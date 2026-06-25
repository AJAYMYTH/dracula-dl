import { createHighlighter, type Highlighter } from 'shiki';

const SAFE_LANGS = new Set([
  'ts', 'tsx', 'js', 'jsx', 'json', 'css', 'html', 'bash', 'py', 'python',
  'go', 'rust', 'java', 'yaml', 'toml', 'md', 'markdown', 'shell', 'sh',
]);

function normalizeLang(lang?: string) {
  if (!lang) return 'txt';
  return SAFE_LANGS.has(lang) ? lang : 'txt';
}

let highlighterPromise: Promise<Highlighter> | null = null;

function getHighlighterInstance() {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighter({
      themes: ['github-dark', 'github-light'],
      langs: ['ts', 'tsx', 'js', 'jsx', 'json', 'css', 'html', 'bash', 'py', 'python', 'yaml', 'md', 'txt'],
    });
  }
  return highlighterPromise;
}

export async function highlightCode(code: string, lang = 'ts') {
  const highlighter = await getHighlighterInstance();
  const safeLang = normalizeLang(lang);

  try {
    return highlighter.codeToHtml(code, {
      lang: safeLang,
      themes: {
        light: 'github-light',
        dark: 'github-dark',
      },
    });
  } catch (err) {
    console.warn('[Shiki error – fallback]', err);
    return `<pre><code>${escapeHtml(code)}</code></pre>`;
  }
}

function escapeHtml(str: unknown) {
  if (typeof str !== 'string') return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
