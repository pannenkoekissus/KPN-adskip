// scratch/find_notification_and_seek.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

// Look for where notification is dispatched or where seeking is cancelled/blocked
const regex = /contentOptions\.indexOf\("TRICKPLAY"\)/g;
let m;
while ((m = regex.exec(content)) !== null) {
  console.log(`=== Match at ${m.index} ===`);
  console.log(content.substring(Math.max(0, m.index - 200), Math.min(content.length, m.index + 300)));
}
