// scratch/inspect_subtitles_mpd.js
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

    const setXml = await send('Runtime.evaluate', {
      expression: `(async () => {
        const p = window._player;
        const uri = p?.getAssetUri ? p.getAssetUri() : null;
        if (!uri) return 'No uri';
        const text = await (await fetch(uri)).text();

        const startIdx = text.indexOf('id="3"');
        const endIdx = text.indexOf('</AdaptationSet>', startIdx);
        return text.substring(startIdx - 15, endIdx + 16);
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Subtitle XML:', JSON.stringify(setXml, null, 2));
    ws.close();
  };
}

main().catch(console.error);
