// scratch/inspect_avs_api.js
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

    const resData = await send('Runtime.evaluate', {
      expression: `(async () => {
        // Let's fetch detail of program 1007885706
        const detailRes = await fetch('https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/CONTENT/DETAIL/PROGRAM/1007885706');
        const detail = await detailRes.json();
        return detail;
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Detail API result:', JSON.stringify(resData, null, 2));
    ws.close();
  };
}

main().catch(console.error);
