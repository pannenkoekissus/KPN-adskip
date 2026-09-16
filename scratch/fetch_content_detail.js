// scratch/fetch_content_detail.js
// Directly fetch CONTENT/DETAIL for the currently open program via CDP
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
      return new Promise((resolve, reject) => {
        const reqId = id++;
        const timeout = setTimeout(() => reject(new Error('Timeout')), 15000);
        const handler = (event) => {
          const data = JSON.parse(event.data);
          if (data.id === reqId) {
            clearTimeout(timeout);
            ws.removeEventListener('message', handler);
            resolve(data.result);
          }
        };
        ws.addEventListener('message', handler);
        ws.send(JSON.stringify({ id: reqId, method, params }));
      });
    }

    // Fetch CONTENT/DETAIL for a known program ID
    // The page is on 1007885714.1, extract the numeric part
    const detailRes = await send('Runtime.evaluate', {
      expression: `(async () => {
        // Try fetching the detail for the current program 
        const programId = '1007885714';
        const url = 'https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/CONTENT/DETAIL/PROGRAM/' + programId;
        const r = await fetch(url, { credentials: 'include' });
        const json = await r.json();
        return json;
      })()`,
      awaitPromise: true,
      returnByValue: true
    });
    
    const fs = require('fs');
    fs.writeFileSync('scratch/content_detail_response.json', JSON.stringify(detailRes, null, 2));
    console.log('Saved CONTENT/DETAIL response to scratch/content_detail_response.json');
    console.log('Keys:', JSON.stringify(Object.keys(detailRes?.value?.resultObj || detailRes?.value || {})));

    // Also fetch CONTENT/VIDEOURL
    const videoUrlRes = await send('Runtime.evaluate', {
      expression: `(async () => {
        const programId = '1007885714';
        // We need deviceId from localStorage
        let deviceId = '';
        for (let i = 0; i < localStorage.length; i++) {
          const k = localStorage.key(i);
          if (k.toLowerCase().includes('device')) {
            const v = localStorage.getItem(k);
            if (v && v.length > 10 && v.length < 100) deviceId = v;
          }
        }
        // Also try sessionStorage
        for (let i = 0; i < sessionStorage.length; i++) {
          const k = sessionStorage.key(i);
          if (k.toLowerCase().includes('device')) {
            const v = sessionStorage.getItem(k);
            if (v && v.length > 10 && v.length < 100 && !deviceId) deviceId = v;
          }
        }
        const url = 'https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/CONTENT/VIDEOURL/PROGRAM/' + programId + '/1?deviceId=' + encodeURIComponent(deviceId) + '&profile=G02';
        const r = await fetch(url, { credentials: 'include' });
        const json = await r.json();
        return { deviceId, url, json };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    fs.writeFileSync('scratch/content_videourl_response.json', JSON.stringify(videoUrlRes, null, 2));
    console.log('Saved CONTENT/VIDEOURL response to scratch/content_videourl_response.json');

    // Also dump EPG raw for RTL 4 to understand structure
    const epgRaw = await send('Runtime.evaluate', {
      expression: `(async () => {
        const url = 'https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/TRAY/EPG?filter_day=0&filter_channelIds=21&extendedChannelMetadata=true';
        const r = await fetch(url, { credentials: 'include' });
        const json = await r.json();
        // Deep extract the structure
        const rtl4 = json.resultObj?.containers?.find(c => c.metadata?.channelId === 21);
        // Show full structure
        return JSON.stringify(rtl4, null, 2).substring(0, 5000);
      })()`,
      awaitPromise: true,
      returnByValue: true
    });
    console.log('RTL4 EPG raw (first 5000 chars):', epgRaw?.value);

    ws.close();
  };
}

main().catch(console.error);
