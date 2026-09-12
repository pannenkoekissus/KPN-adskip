// scratch/test_unlock.js
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

    const testRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        if (!video) return 'No video';

        // 1. Remove KPN's custom restricted currentTime on video element
        const deleted = delete video.currentTime;

        // 2. Also check if setting currentTime now works without restriction
        const before = video.currentTime;
        video.currentTime = before + 10;
        const after = video.currentTime;

        // 3. Unlock the forwards button in DOM
        const fwdBtn = document.querySelector('button[data-t="player-forwards-button"]');
        if (fwdBtn) {
          fwdBtn.removeAttribute('disabled');
          fwdBtn.disabled = false;
        }

        return {
          deleted,
          hasOwnNow: Object.getOwnPropertyDescriptor(video, 'currentTime') !== undefined,
          before,
          after,
          fwdDisabled: fwdBtn ? fwdBtn.disabled : null
        };
      })()`,
      returnByValue: true
    });

    console.log('Unlock test result:', JSON.stringify(testRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
