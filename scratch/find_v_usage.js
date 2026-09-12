// scratch/find_v_usage.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = content.indexOf('[V,F]=x(1/0)');
console.log(content.substring(pos + 12000, pos + 17000));
