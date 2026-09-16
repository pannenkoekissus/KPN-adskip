// scratch/fetch_vzdn_mpd.js
async function main() {
  const res = await fetch('http://localhost:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.id === '7BCDE5C6517F99DE284D777D1EED2D07' || (t.type === 'page' && t.url.includes('tv.kpn.com')));
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

    const mpdData = await send('Runtime.evaluate', {
      expression: `(async () => {
        const entries = performance.getEntriesByType('resource').map(e => e.name);
        const mpdUrl = entries.find(u => u.includes('.mpd'));
        if (!mpdUrl) return 'No mpd found';

        const r = await fetch(mpdUrl);
        const text = await r.text();
        return {
          url: mpdUrl,
          length: text.length,
          fullText: text
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('MPD Length:', mpdData.result?.value?.length);
    if (mpdData.result?.value?.fullText) {
      require('fs').writeFileSync('scratch/current_manifest.mpd', mpdData.result.value.fullText);
      console.log('Saved to scratch/current_manifest.mpd');
    }
    ws.close();
  };
}

main().catch(console.error);
