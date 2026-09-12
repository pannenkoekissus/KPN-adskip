// scratch/inspect_more_back.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = content.indexOf('Ta=420');
console.log(content.substring(pos - 3500, pos - 1500));
