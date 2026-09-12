// scratch/find_dr.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const regex = /var dr=|let dr=|const dr=|dr=\(?([a-zA-Z0-9_$,\s]*)\)?=>/g;
let m;
while ((m = regex.exec(content)) !== null) {
  console.log(`=== Match at ${m.index} ===`);
  console.log(content.substring(Math.max(0, m.index - 50), Math.min(content.length, m.index + 250)));
}
