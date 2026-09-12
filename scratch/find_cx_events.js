// scratch/find_cx_events.js
const fs = require('fs');
const content = fs.readFileSync('scratch/shaka.js', 'utf8');

const pos = content.indexOf('M("shaka.ui.SeekBar",Cx)');
console.log(content.substring(pos - 2500, pos - 1500));
