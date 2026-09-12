// scratch/inspect_gids.js
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

    const info = await send('Runtime.evaluate', {
      expression: `(() => {
        const main = document.querySelector('main') || document.body;
        // find text inside main
        const elementsWithText = Array.from(main.querySelectorAll('*'))
          .filter(e => e.children.length === 0 && e.textContent.trim().length > 1)
          .map(e => e.textContent.trim());
        return {
          totalElements: main.querySelectorAll('*').length,
          sampleTexts: elementsWithText.slice(0, 40),
          channels: Array.from(document.querySelectorAll('img[alt], [aria-label]')).map(e => e.alt || e.getAttribute('aria-label')).slice(0, 20)
        };
      })()`,
      returnByValue: true
    });

    console.log('DOM info:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
