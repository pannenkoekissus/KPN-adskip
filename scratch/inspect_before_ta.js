// scratch/inspect_before_ta.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = content.indexOf('Ta=420');
console.log(content.substring(pos - 1500, pos));
