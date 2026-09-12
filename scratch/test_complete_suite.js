// scratch/test_complete_suite.js
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

    const testSuite = await send('Runtime.evaluate', {
      expression: `(() => {
        const nativeGetter = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime').get;
        const nativeSetter = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime').set;

        // Unlock video seeking
        const video = document.querySelector('video');
        if (video) {
          delete video.currentTime;
        }

        // Enable forward button
        const fwdBtn = document.querySelector('button[data-t="player-forwards-button"]');
        if (fwdBtn) {
          fwdBtn.removeAttribute('disabled');
          fwdBtn.disabled = false;
        }

        // Check markers for program start
        const startMarker = document.querySelector('.shaka_seek-bar-marker_start');
        let progStartTime = null;
        if (startMarker && video && video.duration) {
          const pct = parseFloat(startMarker.style.left);
          if (!isNaN(pct)) {
            progStartTime = (pct / 100) * video.duration;
          }
        }

        return {
          unlocked: !Object.getOwnPropertyDescriptor(video, 'currentTime'),
          progStartTime,
          currentTime: video ? nativeGetter.call(video) : null,
          duration: video ? video.duration : null,
          fwdButtonDisabled: fwdBtn ? fwdBtn.disabled : null
        };
      })()`,
      returnByValue: true
    });

    console.log('Suite test:', JSON.stringify(testSuite, null, 2));
    ws.close();
  };
}

main().catch(console.error);
