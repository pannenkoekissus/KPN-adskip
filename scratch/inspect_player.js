// scratch/inspect_player.js
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

    const evalRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const details = {};
        if (window.shaka) {
          details.shakaVersion = window.shaka.Player ? window.shaka.Player.version : 'exists';
        }
        // find any player instance or video tag
        const videos = Array.from(document.querySelectorAll('video'));
        details.videosCount = videos.length;
        return details;
      })()`,
      returnByValue: true
    });
    console.log('Eval result:', JSON.stringify(evalRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
