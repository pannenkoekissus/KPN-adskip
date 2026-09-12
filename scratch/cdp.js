// scratch/cdp.js
const http = require('http');

async function main() {
  const res = await fetch('http://localhost:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.type === 'page' && t.url.includes('tv.kpn.com'));
  if (!page) {
    console.log('No KPN page found. Targets:', targets);
    return;
  }
  console.log('Found KPN page:', page.title, page.url, page.webSocketDebuggerUrl);

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  ws.onopen = () => {
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

    (async () => {
      const evalRes = await send('Runtime.evaluate', {
        expression: `({
          url: window.location.href,
          title: document.title,
          hasVideo: !!document.querySelector('video'),
          videoSrc: document.querySelector('video')?.src || document.querySelector('video')?.currentSrc || null,
          videoDuration: document.querySelector('video')?.duration || null,
          videoCurrentTime: document.querySelector('video')?.currentTime || null,
          videoPaused: document.querySelector('video')?.paused || null,
          bodyTextSnippets: Array.from(document.querySelectorAll('h1, h2, h3, [class*="title"], [class*="player"]')).slice(0, 10).map(el => el.textContent.trim()).filter(Boolean)
        })`,
        returnByValue: true
      });
      console.log('Runtime eval result:', JSON.stringify(evalRes, null, 2));
      ws.close();
    })();
  };
}

main().catch(console.error);
