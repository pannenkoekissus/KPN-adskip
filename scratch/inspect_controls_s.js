// scratch/inspect_controls_s.js
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

    const sInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        const container = document.querySelector('.shaka-video-container');
        const ui = container?.ui;
        const controls = ui?.getControls();
        const s = controls?.s;

        return {
          ad: s?.ad,
          adManager: !!s?.adManager,
          i: s?.i,
          bar: s?.bar ? s.bar.tagName : null,
          m: s?.m
        };
      })()`,
      returnByValue: true
    });

    console.log('controls.s info:', JSON.stringify(sInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
