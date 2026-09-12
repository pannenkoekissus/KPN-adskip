// scratch/test_shaka_events.js
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

    const testRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const p = window._player;
        if (!p) return 'No player';

        window.__captured_events = [];
        const eventNames = [
          'emsg', 'timelineregionenter', 'timelineregionexit', 'timelineregionadded',
          'metadata', 'trackschanged', 'adaptation', 'buffering', 'loading',
          'unloading', 'ad-started', 'ad-complete', 'ad-break-started', 'ad-break-ended'
        ];

        eventNames.forEach(evt => {
          p.addEventListener(evt, (e) => {
            const detail = { type: evt, detail: e.detail || null, time: Date.now() };
            window.__captured_events.push(detail);
            console.log('[SHAKA EVENT]', evt, e);
          });
        });

        // Also listen on AdManager
        if (p.getAdManager) {
          const am = p.getAdManager();
          if (am && am.addEventListener) {
            eventNames.forEach(evt => {
              am.addEventListener(evt, (e) => {
                window.__captured_events.push({ type: 'AM:' + evt, e });
                console.log('[ADMANAGER EVENT]', evt, e);
              });
            });
          }
        }

        return 'Registered listeners on ' + eventNames.length + ' events';
      })()`,
      returnByValue: true
    });

    console.log('Shaka events setup:', JSON.stringify(testRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
