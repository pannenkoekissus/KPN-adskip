// scratch/test_webaudio.js
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

    const testAudioRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        if (!video) return 'No video';
        try {
          const ac = new (window.AudioContext || window.webkitAudioContext)();
          const src = ac.createMediaElementSource(video);
          const analyser = ac.createAnalyser();
          src.connect(analyser);
          analyser.connect(ac.destination);
          return { success: true, sampleRate: ac.sampleRate };
        } catch (e) {
          return { success: false, error: e.message };
        }
      })()`,
      returnByValue: true
    });

    console.log('Web Audio test:', JSON.stringify(testAudioRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
