// scratch/find_ai.js
const fs = require('fs');
const content = fs.readFileSync('scratch/shaka.js', 'utf8');

const pos = content.indexOf('function Dx(a)');
console.log(content.substring(pos - 1500, pos + 1000));
