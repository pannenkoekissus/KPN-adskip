// scratch/click_play_renze.js
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

    const clickRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const btns = Array.from(document.querySelectorAll('button, a'));
        const playBtn = btns.find(b => b.textContent.includes('Verder kijken') || b.textContent.includes('Vanaf begin kijken'));
        if (playBtn) {
          playBtn.click();
          return 'Clicked: ' + playBtn.textContent.trim();
        }
        return 'No button found';
      })()`,
      returnByValue: true
    });

    console.log('Click result:', clickRes);

    await new Promise(r => setTimeout(r, 4000));

    const check = await send('Runtime.evaluate', {
      expression: `(() => {
        const v = document.querySelector('video');
        return {
          hasVideo: !!v,
          currentTime: v ? v.currentTime : null,
          duration: v ? v.duration : null,
          paused: v ? v.paused : null
        };
      })()`,
      returnByValue: true
    });

    console.log('After click check:', JSON.stringify(check, null, 2));
    ws.close();
  };
}

main().catch(console.error);
