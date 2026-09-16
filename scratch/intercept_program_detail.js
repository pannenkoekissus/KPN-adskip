// scratch/intercept_program_detail.js
// Intercept CONTENT/DETAIL and CONTENT/VIDEOURL responses via CDP Network domain
async function main() {
  const res = await fetch('http://127.0.0.1:9222/json');
  const targets = await res.json();
  const page = targets.find(t => t.type === 'page' && t.url.includes('tv.kpn.com'));
  if (!page) { console.log('No KPN page found'); return; }
  console.log('Attaching to:', page.url);
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

    // Step 1: Find an RTL4 program to inspect via EPG
    const epgRes = await send('Runtime.evaluate', {
      expression: `(async () => {
        const url = 'https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/TRAY/EPG?filter_day=0&filter_channelIds=21&extendedChannelMetadata=true';
        const r = await fetch(url, { credentials: 'include' });
        const json = await r.json();
        const rtl4 = json.resultObj?.containers?.find(c => c.metadata?.channelId === 21);
        // Programs are in nested containers
        const progs = [];
        function findProgs(obj) {
          if (!obj) return;
          if (Array.isArray(obj.containers)) obj.containers.forEach(findProgs);
          if (Array.isArray(obj.elements)) {
            obj.elements.forEach(e => {
              if (e.metadata) progs.push(e);
            });
          }
        }
        findProgs(rtl4);
        return {
          totalProgs: progs.length,
          progs: progs.slice(0, 5).map(p => ({
            id: p.id,
            title: p.metadata?.title,
            airingStartTime: p.metadata?.airingStartTime,
            airingEndTime: p.metadata?.airingEndTime,
            contentOptions: p.metadata?.contentOptions,
            allKeys: Object.keys(p.metadata || {})
          }))
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });
    console.log('EPG Programs:', JSON.stringify(epgRes, null, 2));

    // Step 2: Pick an RTL4 program and fetch its CONTENT/DETAIL
    const progId = epgRes?.value?.progs?.[0]?.id;
    if (progId) {
      const detailRes = await send('Runtime.evaluate', {
        expression: `(async () => {
          const url = 'https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/CONTENT/DETAIL/PROGRAM/' + ${JSON.stringify(progId)};
          const r = await fetch(url, { credentials: 'include' });
          return await r.json();
        })()`,
        awaitPromise: true,
        returnByValue: true
      });
      console.log('CONTENT/DETAIL for', progId, ':', JSON.stringify(detailRes, null, 2));

      const fs = require('fs');
      fs.writeFileSync('scratch/content_detail_response.json', JSON.stringify(detailRes, null, 2));
      console.log('Saved to scratch/content_detail_response.json');
    }

    ws.close();
  };
}

main().catch(console.error);
