'use strict';
const fs = require('node:fs');
const { NaviBay: N } = require('./dist/engine.js');

const csvPath = process.argv[2];
const outPath = process.argv[3];
if (!csvPath || !outPath) {
  throw new Error('Usage: node extract_features.cjs <songs.csv> <out.jsonl>');
}

const dictionaryText = fs.readFileSync('dist/vendor/syllables-th.txt', 'utf8');
const dictionary = dictionaryText.split(/\r?\n/).filter(x => /^[ก-๛]+$/.test(x));
N.setDictionary(dictionary);
fs.writeFileSync('dist/syllables.js', 'globalThis.NAVIBAY_SYLLABLES=' + JSON.stringify(dictionary) + ';');

function parseCsv(s) {
  const rows = []; let row = [], cell = '', quoted = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === '"') { if (quoted && s[i + 1] === '"') { cell += '"'; i++; } else quoted = !quoted; }
    else if (c === ',' && !quoted) { row.push(cell); cell = ''; }
    else if (c === '\n' && !quoted) { row.push(cell.replace(/\r$/, '')); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const header = rows.shift().map(x => x.replace(/^\uFEFF/, ''));
  return rows.filter(r => r.length === header.length).map(r => Object.fromEntries(header.map((k, i) => [k, r[i]])));
}

const raw = parseCsv(fs.readFileSync(csvPath, 'utf8'));
const seen = new Set();
const out = fs.createWriteStream(outPath, { encoding: 'utf8' });

// Header metadata line
out.write(JSON.stringify({ _meta: true, sourceRows: raw.length }) + '\n');

let usable = 0;
for (const r of raw) {
  const key = r.lyrics?.replace(/\s/g, '');
  if (!key || key.length < 30 || seen.has(key) || !/^\d+$/.test(r.views)) continue;
  seen.add(key);
  const a = N.analyze(r.lyrics);
  const group = (r.artist_group || r.artist || r.title || '').trim().toLowerCase();
  const rhymeAll = a.features.filter(f => f.startsWith('r:'));
  const struct = a.features.filter(f => !f.startsWith('w:') && !f.startsWith('r:'));

  // Extract dense 40 features identically to dist/engine.js
  const rawLines = r.lyrics.split(/\r?\n/).map(l => l.trim()).filter(l => l && !/^\[.*\]$/.test(l));
  const lineFreq = new Map();
  let maxLineFreq = 0, dupLines = 0, sumLen = 0, sumLen2 = 0;
  for (const l of rawLines) {
    const norm = l.toLowerCase().replace(/\s+/g, ' ');
    const c = (lineFreq.get(norm) || 0) + 1;
    lineFreq.set(norm, c);
    if (c > maxLineFreq) maxLineFreq = c;
    if (c > 1) dupLines++;
    sumLen += l.length; sumLen2 += l.length * l.length;
  }
  let engWords = 0, numWords = 0, thaiWords = 0, longWords = 0, shortWords = 0;
  const uniqueEng = new Set(), uniqueWords = new Set();
  for (const w of a.tokens) {
    uniqueWords.add(w);
    if (/^[a-z]+$/i.test(w)) { engWords++; uniqueEng.add(w); }
    else if (/^\d+$/.test(w)) numWords++;
    else if (/[ก-๛]/.test(w)) thaiWords++;
    if (w.length >= 6) longWords++;
    if (w.length <= 2) shortWords++;
  }
  const nLines = Math.max(1, rawLines.length || a.lines || 1);
  const avgLen = sumLen / nLines;
  const stdLen = Math.sqrt(Math.max(0, sumLen2 / nLines - avgLen * avgLen));
  const chars = Math.max(1, r.lyrics.length);
  const blankLines = (r.lyrics.match(/\r?\n\s*\r?\n/g) || []).length;
  const nWords = Math.max(1, a.tokens.length);
  const nUnits = Math.max(1, a.units.length);
  const nSections = Math.max(1, a.structures.length);
  const dense = [
    Math.log1p(nWords), Math.log1p(nUnits), Math.log1p(nLines), Math.log1p(uniqueWords.size),
    uniqueWords.size / nWords, dupLines / nLines, Math.log1p(maxLineFreq), lineFreq.size / nLines,
    nWords / nLines, nUnits / nWords, nLines / nSections, Math.log1p(nSections), Math.log1p(blankLines),
    engWords / nWords, Math.log1p(uniqueEng.size), thaiWords / nWords, numWords / nWords,
    longWords / nWords, shortWords / nWords, a.recognized / nUnits,
    Math.log1p(avgLen), Math.log1p(stdLen), stdLen / Math.max(1, avgLen), Math.log1p(chars),
    /\[[^\]]+\]/.test(r.lyrics) ? 1 : 0,
    (r.lyrics.match(/[()]/g) || []).length / nLines,
    (r.lyrics.match(/[!?]/g) || []).length / nLines,
    (r.lyrics.match(/่/g) || []).length / chars,
    (r.lyrics.match(/้/g) || []).length / chars,
    (r.lyrics.match(/๊/g) || []).length / chars,
    (r.lyrics.match(/๋/g) || []).length / chars,
    a.counts.vowel / nUnits, a.counts.onset / nUnits, a.counts.coda / nUnits,
    a.counts.assonance / nUnits, a.counts.near / nUnits, a.counts.repeat / nUnits,
    a.counts.multi / nLines, a.counts.phrase / nLines,
    (a.counts.vowel + a.counts.multi) / nLines
  ];

  out.write(JSON.stringify({
    group,
    views: Number(r.views),
    tokens: a.tokens,
    rhymes: rhymeAll,
    struct,
    dense
  }) + '\n');
  usable++;
  if (usable % 1000 === 0) console.log(`Extracted phonetic features: ${usable} songs`);
}
out.end();
console.log(`Finished extraction: ${usable} usable songs from ${raw.length} rows`);
