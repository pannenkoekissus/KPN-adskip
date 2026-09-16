// scratch/search_ad_insertion.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const queries = ['ad-started', 'ad-stopped', 'requestClientSideAds', 'requestServerSideStream', 'adManager', 'adBreak', 'adPod', 'ima', 'vast'];

for (const q of queries) {
  let pos = 0;
  let count = 0;
  console.log(`=== Query: ${q} ===`);
  while (count < 3) {
    const idx = content.indexOf(q, pos);
    if (idx === -1) break;
    console.log(`[${idx}] ` + content.substring(Math.max(0, idx - 80), Math.min(content.length, idx + 150)));
    pos = idx + q.length + 20;
    count++;
  }
}
