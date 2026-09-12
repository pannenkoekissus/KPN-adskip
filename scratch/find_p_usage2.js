// scratch/find_p_usage2.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = 509593;
const chunk = content.substring(pos, pos + 15000);
const regex = /P\.current/g;
let m;
while ((m = regex.exec(chunk)) !== null) {
  console.log(`Match at ${m.index}:`);
  console.log(chunk.substring(Math.max(0, m.index - 100), Math.min(chunk.length, m.index + 200)));
}
