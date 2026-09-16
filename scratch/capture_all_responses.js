// scratch/capture_all_responses.js
const fs = require('fs');

async function main() {
  const res = await fetch('http://localhost:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.id === '7BCDE5C6517F99DE284D777D1EED2D07' || (t.type === 'page' && t.url.includes('tv.kpn.com')));
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

    await send('Network.enable');

    const capturedBodies = [];

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.method === 'Network.responseReceived') {
          const resp = data.params.response;
          const url = resp.url;
          const type = resp.mimeType || '';
          if (type.includes('json') || type.includes('xml') || type.includes('text') || /ad|cue|timeline|track|meta|emp/i.test(url)) {
            // Get response body
            send('Network.getResponseBody', { requestId: data.params.requestId }).then(bodyRes => {
              if (bodyRes && bodyRes.body) {
                capturedBodies.push({ url, body: bodyRes.body.substring(0, 500) });
                if (/ad|commercial|break|cue|spot|vast/i.test(bodyRes.body)) {
                  console.log('🎯 [MATCHED AD DATA]', url);
                  fs.appendFileSync('scratch/ad_matches.txt', `URL: ${url}\nBODY: ${bodyRes.body}\n\n---\n\n`);
                }
              }
            }).catch(() => {});
          }
        }
      } catch (e) {}
    };

    console.log('Listening to network traffic for 12 seconds...');
    await new Promise(r => setTimeout(r, 12000));

    console.log('Total captured bodies:', capturedBodies.length);
    ws.close();
  };
}

main().catch(console.error);
