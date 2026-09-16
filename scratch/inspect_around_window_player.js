// scratch/inspect_around_window_player.js
const fs = require('fs');
const content = fs.readFileSync('scratch/app.js', 'utf8');

const pos = content.indexOf('window._player=h.player=ne');
console.log(content.substring(pos - 1500, pos + 1500));
