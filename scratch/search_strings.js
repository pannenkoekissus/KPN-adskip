// scratch/search_strings.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const regex = /"([^"\\]*(?:\\.[^"\\]*)*)"/g;
let match;
const found = new Set();
while ((match = regex.exec(content)) !== null) {
  const str = match[1];
  if (/reclame|commercial|spoel|blokkeer|adbreak|ad[-_]break|trickplay/i.test(str)) {
    found.add(str);
  }
}
console.log('Found strings in app.js:', Array.from(found));
