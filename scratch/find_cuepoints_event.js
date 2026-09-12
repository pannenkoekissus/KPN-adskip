// scratch/find_cuepoints_event.js
const fs = require('fs');
const content = fs.readFileSync('scratch/shaka.js', 'utf8');

const pos = content.indexOf('{c.i=d.cuepoints;Gx(c)}');
console.log(content.substring(pos - 600, pos + 100));
