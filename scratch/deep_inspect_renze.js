// scratch/deep_inspect_renze.js
async function main() {
  const res = await fetch('http://localhost:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.id === '7BCDE5C6517F99DE284D777D1EED2D07' || (t.type === 'page' && t.url.includes('tv.kpn.com')));
  if (!page) {
    console.log('Page not found. Targets:', targets);
    return;
  }
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

    const data = await send('Runtime.evaluate', {
      expression: `(async () => {
        const video = document.querySelector('video');
        const p = window._player;
        const entries = performance.getEntriesByType('resource').map(e => e.name);

        // Fetch detail of program 1007877596
        let detail = null;
        try {
          const r = await fetch('https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/CONTENT/DETAIL/PROGRAM/1007877596');
          detail = await r.json();
        } catch (e) {
          detail = e.message;
        }

        // Check if there are other API requests with words like timeline, cue, segment, epg, chapter
        const apiRequests = entries.filter(u => u.includes('api-avs') || u.includes('kpnstreaming') || u.includes('emp'));

        return {
          title: document.title,
          url: window.location.href,
          hasVideo: !!video,
          currentTime: video ? video.currentTime : null,
          duration: video ? video.duration : null,
          hasPlayer: !!p,
          detail,
          apiRequests
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Deep inspect Renze:', JSON.stringify(data, null, 2));
    ws.close();
  };
}

main().catch(console.error);
