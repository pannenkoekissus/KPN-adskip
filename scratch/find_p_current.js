// scratch/find_p_current.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = 509593;
console.log(content.substring(pos, pos + 3000));
