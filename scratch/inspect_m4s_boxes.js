// scratch/inspect_m4s_boxes.js
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

    const boxInfo = await send('Runtime.evaluate', {
      expression: `(async () => {
        // Fetch a segment from performance entries
        const entries = performance.getEntriesByType('resource');
        const seg = entries.find(e => e.name.includes('.m4s') && e.name.includes('video'));
        if (!seg) return 'No segment found';

        const r = await fetch(seg.name);
        const buf = await r.arrayBuffer();
        const bytes = new Uint8Array(buf);

        // Scan for 4-letter box types
        const boxes = [];
        let pos = 0;
        const view = new DataView(buf);
        while (pos < bytes.length - 8) {
          const size = view.getUint32(pos);
          let type = '';
          for (let i = 0; i < 4; i++) {
            type += String.fromCharCode(bytes[pos + 4 + i]);
          }
          boxes.push({ type, size, pos });
          if (size <= 0 || size > 10000000) break;
          pos += size;
        }

        return {
          segUrl: seg.name.split('/').pop(),
          totalBytes: bytes.length,
          boxes
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Segment box info:', JSON.stringify(boxInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
