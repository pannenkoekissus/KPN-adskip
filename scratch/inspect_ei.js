// scratch/inspect_ei.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = content.indexOf('seekLimitRange:');
console.log(content.substring(pos - 1000, pos + 500));
