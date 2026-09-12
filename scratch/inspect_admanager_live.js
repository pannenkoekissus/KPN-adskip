// scratch/inspect_admanager_live.js
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

    const adInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        const p = window._player;
        const am = p?.getAdManager();
        return {
          hasGoogleIma: !!window.google?.ima,
          adManagerKeys: am ? Object.keys(am) : [],
          adManagerValues: am ? {
            cuePoints: am.cuePoints || am.i || am.g,
            isServerSide: !!am.serverSide,
            isClientSide: !!am.clientSide
          } : null
        };
      })()`,
      returnByValue: true
    });

    console.log('AdManager live:', JSON.stringify(adInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
