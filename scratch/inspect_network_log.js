// scratch/inspect_network_log.js
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

    // Inspect performance entries for network requests
    const perfInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        const entries = performance.getEntriesByType('resource');
        return entries
          .filter(e => !e.name.includes('.svg') && !e.name.includes('.png') && !e.name.includes('.jpg') && !e.name.includes('.css') && !e.name.includes('chunk'))
          .map(e => ({
            name: e.name,
            initiatorType: e.initiatorType,
            duration: e.duration
          }));
      })()`,
      returnByValue: true
    });

    console.log('Network entries:', JSON.stringify(perfInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
