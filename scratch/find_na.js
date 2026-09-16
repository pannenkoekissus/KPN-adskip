// scratch/find_na.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = 567275;
console.log(content.substring(pos - 4000, pos - 2500));
