// scratch/find_all_api_endpoints.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

// Find all strings starting with / or http
const regex = /"(https?:\/\/[^"\\]+|\/[A-Z0-9_/]+)"/g;
let m;
const paths = new Set();
while ((m = regex.exec(content)) !== null) {
  paths.add(m[1]);
}
console.log('API Paths found in app.js:', Array.from(paths));
