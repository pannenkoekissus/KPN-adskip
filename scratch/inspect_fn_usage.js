// scratch/inspect_fn_usage.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = 567275;
console.log(content.substring(pos - 1000, pos + 1500));
