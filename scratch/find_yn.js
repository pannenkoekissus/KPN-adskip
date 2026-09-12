// scratch/find_yn.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = 191029;
console.log(content.substring(pos - 300, pos + 100));
