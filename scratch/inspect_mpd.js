// scratch/inspect_mpd.js
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

    const mpdInfo = await send('Runtime.evaluate', {
      expression: `(async () => {
        const player = window._player;
        const uri = player?.getAssetUri ? player.getAssetUri() : null;
        if (!uri) return 'No uri';

        const res = await fetch(uri);
        const text = await res.text();
        return {
          length: text.length,
          hasPeriods: (text.match(/<Period/g) || []).length,
          hasEventStream: text.includes('EventStream'),
          hasScte: text.includes('scte') || text.includes('SCTE'),
          hasAd: text.includes('ad') || text.includes('Ad') || text.includes('break'),
          snippet: text.substring(0, 1500)
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('MPD info:', JSON.stringify(mpdInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
