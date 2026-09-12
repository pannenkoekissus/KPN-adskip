// scratch/search_restriction_code.js
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

    const scriptSearchResults = await send('Runtime.evaluate', {
      expression: `(async () => {
        const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        const appScripts = scripts.filter(s => s.includes('app') || s.includes('vendor') || s.includes('player') || s.includes('bundle') || s.includes('chunk'));
        
        const matches = [];
        for (const src of appScripts) {
          try {
            const r = await fetch(src);
            const text = await r.text();
            const terms = ['doorspoelen', 'trickplay', 'adBreak', 'commercial', 'sotvTrickplay', 'contractRestriction'];
            for (const t of terms) {
              let idx = text.toLowerCase().indexOf(t.toLowerCase());
              if (idx !== -1) {
                matches.push({
                  src: src.split('/').pop(),
                  term: t,
                  snippet: text.substring(Math.max(0, idx - 100), Math.min(text.length, idx + 150))
                });
              }
            }
          } catch(e) {}
        }
        return { appScriptsCount: appScripts.length, matches: matches.slice(0, 20) };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Search results:', JSON.stringify(scriptSearchResults, null, 2));
    ws.close();
  };
}

main().catch(console.error);
