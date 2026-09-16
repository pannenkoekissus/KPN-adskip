// scratch/inspect_body_text.js
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

    const check = await send('Runtime.evaluate', {
      expression: `(() => {
        const playBtn = document.querySelector('[data-t*="play"], [class*="play"], button');
        const h1 = document.querySelector('h1, h2');
        return {
          h1: h1 ? h1.textContent : null,
          playBtn: playBtn ? playBtn.outerHTML.substring(0, 200) : null,
          bodySnippet: document.body.innerText.substring(0, 500)
        };
      })()`,
      returnByValue: true
    });

    console.log('Body check:', JSON.stringify(check, null, 2));
    ws.close();
  };
}

main().catch(console.error);
