// scratch/fetch_ttml_segment.js
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

    const ttmlInfo = await send('Runtime.evaluate', {
      expression: `(async () => {
        const p = window._player;
        const uri = p?.getAssetUri ? p.getAssetUri() : null;
        if (!uri) return 'No uri';

        // Construct a subtitle segment URL
        // Base: uri up to last /
        const base = uri.substring(0, uri.lastIndexOf('/') + 1) + 'dash/';
        const initUrl = base + 'VzdM-textstream_dut=1000.dash';
        const segUrl = base + 'VzdM-textstream_dut=1000-10.m4s';

        try {
          const rInit = await fetch(initUrl);
          const initBuf = await rInit.arrayBuffer();
          const rSeg = await fetch(segUrl);
          const segBuf = await rSeg.arrayBuffer();

          const segText = new TextDecoder().decode(segBuf);
          const hasXml = segText.includes('<tt') || segText.includes('<p') || segText.includes('xml');

          return {
            initBytes: initBuf.byteLength,
            segBytes: segBuf.byteLength,
            hasXml,
            snippet: segText.replace(/[^\\x20-\\x7E]/g, ' ').substring(0, 300)
          };
        } catch (e) {
          return { error: e.message };
        }
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('TTML segment fetch:', JSON.stringify(ttmlInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
