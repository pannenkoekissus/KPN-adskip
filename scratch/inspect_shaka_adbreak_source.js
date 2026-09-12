// scratch/inspect_shaka_adbreak_source.js
const fs = require('fs');
const content = fs.readFileSync('scratch/shaka.js', 'utf8');

// Find occurrences of seekBarColors.adBreaks
let pos = 0;
while (true) {
  const idx = content.indexOf('seekBarColors.adBreaks', pos);
  if (idx === -1) break;
  console.log(`=== Match at ${idx} ===`);
  console.log(content.substring(Math.max(0, idx - 400), Math.min(content.length, idx + 400)));
  pos = idx + 30;
}
