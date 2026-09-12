// scratch/test_inject_userscript.js
const fs = require('fs');

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

    const scriptCode = fs.readFileSync('kpn-adskip.user.js', 'utf8');

    const injectRes = await send('Runtime.evaluate', {
      expression: scriptCode,
      returnByValue: true
    });

    console.log('Injection result:', injectRes);

    await new Promise(r => setTimeout(r, 1500));

    // Verify DOM state
    const verifyRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const bar = document.getElementById('kpn-adskip-control-bar');
        const fwdBtn = document.querySelector('button[data-t="player-forwards-button"]');
        const video = document.querySelector('video');

        return {
          hasBar: !!bar,
          barButtons: bar ? Array.from(bar.querySelectorAll('button')).map(b => b.textContent.trim()) : [],
          fwdBtnDisabled: fwdBtn ? fwdBtn.disabled : null,
          videoTime: video ? video.currentTime : null,
          videoDuration: video ? video.duration : null,
          videoHasOwnTime: !!(video && Object.getOwnPropertyDescriptor(video, 'currentTime'))
        };
      })()`,
      returnByValue: true
    });

    console.log('Verification result:', JSON.stringify(verifyRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
