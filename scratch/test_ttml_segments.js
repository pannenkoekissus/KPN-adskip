// scratch/test_ttml_segments.js
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

    const testRes = await send('Runtime.evaluate', {
      expression: `(async () => {
        const p = window._player;
        const uri = p?.getAssetUri ? p.getAssetUri() : null;
        if (!uri) return 'No uri';

        const base = uri.substring(0, uri.lastIndexOf('/') + 1) + 'dash/';
        
        // Let's test segment numbers around current time (current time ~800s => 800 / 5.76 = ~138)
        const currentSegNum = Math.floor(800 / 5.76);
        const results = [];

        // Check 10 segments around 138
        for (let i = currentSegNum - 5; i <= currentSegNum + 5; i++) {
          const segUrl = base + 'Vxjh-textstream_dut=1000-' + i + '.m4s';
          try {
            const r = await fetch(segUrl);
            const buf = await r.arrayBuffer();
            const text = new TextDecoder().decode(buf);
            const hasCues = text.includes('<p') || text.includes('xml:id') || text.includes('begin=');
            
            // Extract text inside <p> or <span>
            const pMatches = text.match(/<p[^>]*>(.*?)<\\/p>/g) || [];
            results.push({
              seg: i,
              time: Math.round(i * 5.76),
              byteLength: buf.byteLength,
              hasCues,
              dialogue: pMatches.map(m => m.replace(/<[^>]*>/g, '').trim()).filter(Boolean)
            });
          } catch(e) {
            results.push({ seg: i, error: e.message });
          }
        }

        return results;
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('TTML segments test:', JSON.stringify(testRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
