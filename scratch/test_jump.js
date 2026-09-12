// scratch/test_jump.js
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

    const testJumpRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        if (!video) return 'No video found';

        const nativeGetter = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime').get;
        const nativeSetter = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime').set;

        const before = nativeGetter.call(video);

        // Find ad end time
        const start = document.querySelector('.shaka_seek-bar-marker_start');
        const end = document.querySelector('.shaka_seek-bar-marker_end');
        let endPct = end && end.style.right ? (100 - parseFloat(end.style.right)) : null;
        let targetTime = (endPct !== null && video.duration) ? ((endPct / 100) * video.duration) + 1 : before + 300;

        console.log('Jumping from', before, 'to target:', targetTime);
        nativeSetter.call(video, targetTime);

        // Also trigger play if paused or dispatch seeking event if needed
        const after = nativeGetter.call(video);
        return {
          before,
          after,
          targetTime,
          paused: video.paused
        };
      })()`,
      returnByValue: true
    });

    console.log('Jump result:', JSON.stringify(testJumpRes, null, 2));

    // Wait 2 seconds and check if playback resumes / position holds
    await new Promise(r => setTimeout(r, 2000));

    const checkRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        const nativeGetter = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime').get;
        return {
          currentTime: video ? nativeGetter.call(video) : null,
          paused: video ? video.paused : null
        };
      })()`,
      returnByValue: true
    });

    console.log('After 2s check:', JSON.stringify(checkRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
