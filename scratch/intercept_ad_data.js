// scratch/intercept_ad_data.js
async function main() {
  const res = await fetch('http://127.0.0.1:9222/json');
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

    const netData = await send('Runtime.evaluate', {
      expression: `(async () => {
        const entries = performance.getEntriesByType('resource');
        // Let's inspect all URLs
        const allUrls = entries.map(e => e.name);

        // Check if there are requests containing ad, vast, vmap, spot, smart, epg, cue, smartadserver, springserve, freewheel, pubmatic, rubicon, appnexus, kpn, avs
        const potentialAdUrls = allUrls.filter(u => {
          const lower = u.toLowerCase();
          return !lower.includes('.m4s') && !lower.includes('.dash') && !lower.includes('.svg') && !lower.includes('.png') && !lower.includes('.jpg') && !lower.includes('.woff') && !lower.includes('analytics');
        });

        // Search window for any ad data objects or state
        const winKeys = Object.keys(window).filter(k => /ad|vast|vmap|spot|break/i.test(k));

        return {
          currentUrl: window.location.href,
          title: document.title,
          allUrlsCount: allUrls.length,
          potentialAdUrls,
          winKeys
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Network & Ad URLs:', JSON.stringify(netData, null, 2));
    ws.close();
  };
}

main().catch(console.error);
