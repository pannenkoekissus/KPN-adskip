// scratch/test_canvas_drm.js
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
        const canvas = document.createElement('canvas');
        canvas.width = 100;
        canvas.height = 100;
        const ctx = canvas.getContext('2d');
        try {
          ctx.drawImage(video, 0, 0, 100, 100);
          const data = ctx.getImageData(0, 0, 10, 10).data;
          return { success: true, sample: Array.from(data.slice(0, 12)) };
        } catch (e) {
          return { success: false, error: e.message };
        }
      })()`,
      returnByValue: true
    });

    console.log('Canvas DRM test:', JSON.stringify(testRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
