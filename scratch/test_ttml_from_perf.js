// scratch/test_ttml_from_perf.js
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
        const entries = performance.getEntriesByType('resource').map(e => e.name);
        const mpdEntry = entries.find(u => u.includes('.mpd'));
        if (!mpdEntry) return { error: 'No MPD in perf entries', count: entries.length };

        const base = mpdEntry.substring(0, mpdEntry.lastIndexOf('/') + 1) + 'dash/';
        // Find segment prefix from any video segment in perf
        const videoEntry = entries.find(u => u.includes('-video='));
        const prefix = videoEntry ? videoEntry.split('/').pop().split('-')[0] : 'Vxjh';

        const results = [];
        // Test 10 segments around 800s (segment ~138)
        for (let i = 135; i <= 145; i++) {
          const segUrl = base + prefix + '-textstream_dut=1000-' + i + '.m4s';
          try {
            const r = await fetch(segUrl);
            const buf = await r.arrayBuffer();
            const text = new TextDecoder().decode(buf);
            const pMatches = text.match(/<p[^>]*>(.*?)<\\/p>/gi) || [];
            results.push({
              seg: i,
              time: Math.round(i * 5.76),
              bytes: buf.byteLength,
              hasText: pMatches.length > 0,
              dialogue: pMatches.map(m => m.replace(/<[^>]*>/g, '').trim()).filter(Boolean)
            });
          } catch(e) {
            results.push({ seg: i, error: e.message });
          }
        }

        return {
          prefix,
          results
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('TTML from perf result:', JSON.stringify(testRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
