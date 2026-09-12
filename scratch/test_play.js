// scratch/test_play.js
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

    const playRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        if (video) {
          video.play().catch(err => console.error(err));
          return {
            currentTime: video.currentTime,
            paused: video.paused
          };
        }
        return 'No video';
      })()`,
      returnByValue: true
    });

    console.log('Play result:', playRes);

    await new Promise(r => setTimeout(r, 2000));

    const checkRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        return {
          currentTime: video ? video.currentTime : null,
          paused: video ? video.paused : null
        };
      })()`,
      returnByValue: true
    });

    console.log('After 2s:', checkRes);
    ws.close();
  };
}

main().catch(console.error);
