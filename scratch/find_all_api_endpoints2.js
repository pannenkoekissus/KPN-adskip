// scratch/find_all_api_endpoints2.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app-prettier.js', 'utf8');
const lines = content.split('\n');
const endpoints = new Set();
lines.forEach(l => {
  const m = l.match(/['"]\/(CONTENT|TRAY|USER|AUTH|STREAM|PLAYER|METADATA|EPG|PROGRAM|SUBSCRIPTION)[^'"]*['"]/g);
  if (m) m.forEach(x => endpoints.add(x));
});
console.log('Endpoints:', [...endpoints]);
