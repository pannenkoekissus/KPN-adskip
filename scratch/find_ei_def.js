// scratch/find_ei_def.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = content.indexOf('var Ei=');
if (pos !== -1) {
  console.log(content.substring(pos, pos + 3000));
} else {
  const m = content.match(/(?:var|let|const)\s+Ei\s*=/);
  if (m) {
    console.log(content.substring(m.index, m.index + 3000));
  } else {
    console.log('Not found directly');
  }
}
