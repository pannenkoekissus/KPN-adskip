// scratch/inspect_preact.js
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

    const resInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        const fwdBtn = document.querySelector('button[data-t="player-forwards-button"]');
        const vContainer = document.querySelector('.shaka-video-container');
        const root = document.querySelector('#app') || document.body;
        
        return {
          fwdKeys: fwdBtn ? Object.keys(fwdBtn).filter(k => k.startsWith('_')) : [],
          containerKeys: vContainer ? Object.keys(vContainer).filter(k => k.startsWith('_')) : [],
          rootKeys: root ? Object.keys(root).filter(k => k.startsWith('_')) : []
        };
      })()`,
      returnByValue: true
    });

    console.log('Preact keys:', JSON.stringify(resInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
