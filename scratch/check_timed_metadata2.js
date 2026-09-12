// scratch/check_timed_metadata2.js
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

    const resMetadata = await send('Runtime.evaluate', {
      expression: `(() => {
        const p = window._player;
        if (!p) return 'No _player';

        const manifest = p.getManifest ? p.getManifest() : null;
        return {
          periodsCount: manifest?.periods?.length,
          periods: manifest?.periods?.map(period => ({
            id: period.id,
            startTime: period.startTime,
            textStreamsCount: period.textStreams?.length,
            eventStreamsCount: period.eventStreams?.length
          }))
        };
      })()`,
      returnByValue: true
    });

    console.log('Timed metadata 2:', JSON.stringify(resMetadata, null, 2));
    ws.close();
  };
}

main().catch(console.error);
