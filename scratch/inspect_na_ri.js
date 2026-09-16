// scratch/inspect_na_ri.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = 567275;
console.log(content.substring(pos - 1500, pos));
