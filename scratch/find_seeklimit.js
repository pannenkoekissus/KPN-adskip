// scratch/find_seeklimit.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const regex = /seekLimitRange/g;
let m;
while ((m = regex.exec(content)) !== null) {
  console.log(`=== Match at ${m.index} ===`);
  console.log(content.substring(Math.max(0, m.index - 100), Math.min(content.length, m.index + 200)));
}
