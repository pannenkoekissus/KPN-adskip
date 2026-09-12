// scratch/find_fn_state.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = 567275;
console.log(content.substring(pos - 6000, pos - 4000));
