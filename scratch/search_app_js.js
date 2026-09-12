// scratch/search_app_js.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const queries = ['trickplay', 'seeking', 'seek', 'restriction', 'sotv', 'cutv', 'contract', 'adBreak', 'commercial', 'doorspoelen', 'replay', 'fastforward', 'forward'];

for (const q of queries) {
  let count = 0;
  let pos = 0;
  console.log(`=== Query: ${q} ===`);
  while (count < 5) {
    const idx = content.toLowerCase().indexOf(q.toLowerCase(), pos);
    if (idx === -1) break;
    console.log(`[${idx}] ` + content.substring(Math.max(0, idx - 80), Math.min(content.length, idx + 120)).replace(/\n/g, ' '));
    pos = idx + q.length + 20;
    count++;
  }
}
