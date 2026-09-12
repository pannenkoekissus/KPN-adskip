// scratch/find_react_root.js
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
        const all = Array.from(document.querySelectorAll('*'));
        const reactRoots = [];
        for (const el of all) {
          for (const k in el) {
            if (k.startsWith('_reactRootContainer') || k.startsWith('__reactFiber') || k.startsWith('__reactContainer')) {
              reactRoots.push({ tag: el.tagName, id: el.id, className: el.className, key: k });
              break;
            }
          }
          if (reactRoots.length > 5) break;
        }
        return reactRoots;
      })()`,
      returnByValue: true
    });

    console.log('React roots:', JSON.stringify(resInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
