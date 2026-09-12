// scratch/search_empclient.js
async function main() {
  const res = await fetch('http://localhost:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.type === 'page' && t.url.includes('tv.kpn.com'));
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  
  ws.onopen = async () => {
    let id = 1;
    function send(method, params = {}) {
      return new Promise((resolve) => {
        const reqId = id++;
        const handler = (event) => {
          const data = JSON.parse(event.data);
          if (data.id === reqId) {
            ws.removeEventListener('message', handler);
            resolve(data.result);
          }
        };
        ws.addEventListener('message', handler);
        ws.send(JSON.stringify({ id: reqId, method, params }));
      });
    }

    const searchRes = await send('Runtime.evaluate', {
      expression: `(async () => {
        const scripts = ['https://tv.kpn.com/empclient.min.js', 'https://tv.kpn.com/platform.min.js'];
        const matches = [];
        for (const s of scripts) {
          const text = await (await fetch(s)).text();
          const terms = ['trickplay', 'adBreak', 'commercial', 'contract', 'restriction', 'canSeek', 'isSeekAllowed', 'allowSeek', 'disableSeek', 'blocked'];
          for (const t of terms) {
            let pos = 0;
            while (true) {
              const idx = text.toLowerCase().indexOf(t.toLowerCase(), pos);
              if (idx === -1) break;
              matches.push({
                script: s.split('/').pop(),
                term: t,
                snippet: text.substring(Math.max(0, idx - 80), Math.min(text.length, idx + 120))
              });
              pos = idx + t.length + 50;
              if (matches.length > 30) break;
            }
          }
        }
        return matches;
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('EMP Client matches:', JSON.stringify(searchRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
