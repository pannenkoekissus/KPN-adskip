// scratch/search_marker_script.js
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

    const info = await send('Runtime.evaluate', {
      expression: `(() => {
        // Find scripts or function definitions mentioning shaka_seek-bar-marker
        const scripts = Array.from(document.querySelectorAll('script')).map(s => s.src || s.textContent.substring(0, 100));
        
        // Let's inspect window objects or Vue/component data around the player
        const markerStart = document.querySelector('.shaka_seek-bar-marker_start');
        const markerEnd = document.querySelector('.shaka_seek-bar-marker_end');

        // Check if there are data properties on the marker elements
        const markerProps = markerStart ? Object.keys(markerStart) : [];
        const containerProps = markerStart?.parentElement ? Object.keys(markerStart.parentElement) : [];

        // Check if there is an ad object or markers array in the player UI or Vue/store
        let storeState = null;
        if (window.__INITIAL_STATE__ || window.__STORE__ || window.store) {
          storeState = 'has store';
        }

        return {
          markerProps,
          containerProps: containerProps.filter(k => k.startsWith('__')),
          startStyle: markerStart?.getAttribute('style'),
          endStyle: markerEnd?.getAttribute('style')
        };
      })()`,
      returnByValue: true
    });

    console.log('Script search:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
