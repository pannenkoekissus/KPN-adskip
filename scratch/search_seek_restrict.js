// scratch/search_seek_restrict.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const regex = /seekBar|seekRange|seekTo|isSeeking|onSeek/gi;
let m;
let count = 0;
while ((m = regex.exec(content)) !== null && count < 10) {
  console.log(`[${m.index}] ` + content.substring(Math.max(0, m.index - 80), Math.min(content.length, m.index + 120)));
  count++;
}
