// scratch/fetch_epg_via_cdp.js
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
        const url = 'https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/TRAY/EPG?filter_day=0&filter_channelIds=18,19,20,21,22,23,24,25,26,27,29,3&extendedChannelMetadata=true';
        const r = await fetch(url, { credentials: 'include' });
        const json = await r.json();
        
        // Return summary of channels and their programs
        const rtl4Container = json.resultObj?.containers?.find(c => c.metadata?.channelId === 21);
        return {
          rtl4Metadata: rtl4Container?.metadata,
          keys: Object.keys(rtl4Container || {}),
          elements: (rtl4Container?.elements || rtl4Container?.items || rtl4Container?.programs || []).slice(0, 10)
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('EPG via CDP:', JSON.stringify(evalRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
