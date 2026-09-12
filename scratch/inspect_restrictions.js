// scratch/inspect_restrictions.js
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

    const restrictionInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        // Let's inspect the video element's event listeners
        const video = document.querySelector('video');
        
        // Let's inspect the seek-bar element
        const seekBar = document.querySelector('.shaka-seek-bar');
        const container = document.querySelector('.shaka-video-container');
        const ui = container?.ui;
        const controls = ui?.getControls();

        // Check if there are any messages or toasts configured in the app for "doorspoelen"
        // Let's search strings in window
        return {
          seekBarDisabled: seekBar ? seekBar.disabled : null,
          seekBarReadOnly: seekBar ? seekBar.readOnly : null,
          videoSeeking: video ? video.seeking : null
        };
      })()`,
      returnByValue: true
    });

    console.log('Restriction info:', JSON.stringify(restrictionInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
