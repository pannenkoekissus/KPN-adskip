// scratch/find_rtl_shows.js
async function main() {
  const res = await fetch('http://127.0.0.1:9222/json');
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

    const evalRes = await send('Runtime.evaluate', {
      expression: `(async () => {
        const chanRes = await fetch('https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/TRAY/LIVECHANNELS?orderBy=orderId&sortOrder=asc&from=0&to=100');
        const chans = await chanRes.json();
        const allElements = [];
        (chans.resultObj?.containers || []).forEach(c => {
          (c.elements || []).forEach(e => allElements.push(e));
        });
        return (chans.resultObj?.containers || []).map(c => ({
          keys: Object.keys(c),
          elementsCount: c.elements ? c.elements.length : (c.items ? c.items.length : null),
          type: c.type || c.layout
        }));
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('RTL 4 catchup programs:', JSON.stringify(evalRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
