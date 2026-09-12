// scratch/test_playback_rate.js
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

    const testRate = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        if (!video) return 'No video';
        const orig = video.playbackRate;
        video.playbackRate = 8;
        const current = video.playbackRate;
        setTimeout(() => { video.playbackRate = 1; }, 2000);
        return { orig, current };
      })()`,
      returnByValue: true
    });

    console.log('Playback rate test:', JSON.stringify(testRate, null, 2));
    ws.close();
  };
}

main().catch(console.error);
