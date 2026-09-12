// scratch/inspect_videourl_response.js
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

    const data = await send('Runtime.evaluate', {
      expression: `(async () => {
        // Find performance entry for VIDEOURL
        const entries = performance.getEntriesByType('resource');
        const videoUrlEntry = entries.find(e => e.name.includes('/CONTENT/VIDEOURL/'));
        if (!videoUrlEntry) return 'No VIDEOURL entry found';

        const r = await fetch(videoUrlEntry.name);
        return await r.json();
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('VIDEOURL JSON:', JSON.stringify(data, null, 2));
    ws.close();
  };
}

main().catch(console.error);
