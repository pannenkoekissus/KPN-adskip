// scratch/find_trickplay_lock.js
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
        const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        const appScript = scripts.find(s => s.includes('app.'));
        if (!appScript) return 'No app script';
        const text = await (await fetch(appScript)).text();

        // Search for trickplay / seek blocking logic
        const regexes = [
          /([a-zA-Z0-9_$]+)\s*:\s*function[^{]*\{[^}]*trickplay[^}]*\}/gi,
          /isTrickplay[a-zA-Z0-9_$]*/gi,
          /TRICKPLAY[a-zA-Z0-9_$]*/gi,
          /[a-zA-Z0-9_$.]+\.isSOTVTrickplayEnabled/gi,
          /[a-zA-Z0-9_$.]*doorspoelen[a-zA-Z0-9_$.]*/gi,
          /fastForward[a-zA-Z0-9_$]*/gi
        ];

        const matches = {};
        for (const reg of regexes) {
          const found = text.match(reg);
          if (found) {
            matches[reg.toString()] = Array.from(new Set(found)).slice(0, 10);
          }
        }

        // Also find snippets around "doorspoelen" or where seek is prevented
        const doorIdx = text.toLowerCase().indexOf('doorspoelen');
        let doorSnippet = null;
        if (doorIdx !== -1) {
          doorSnippet = text.substring(Math.max(0, doorIdx - 200), Math.min(text.length, doorIdx + 300));
        }

        // Find snippets around SOTVTrickplay
        const sotvIdx = text.indexOf('isSOTVTrickplayEnabled');
        let sotvSnippet = null;
        if (sotvIdx !== -1) {
          sotvSnippet = text.substring(Math.max(0, sotvIdx - 200), Math.min(text.length, sotvIdx + 300));
        }

        return {
          matches,
          doorSnippet,
          sotvSnippet
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Search trickplay lock:', JSON.stringify(searchRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
