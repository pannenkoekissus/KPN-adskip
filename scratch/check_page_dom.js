// scratch/check_page_dom.js
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

    const state = await send('Runtime.evaluate', {
      expression: `(() => {
        const v = document.querySelector('video');
        return {
          url: window.location.href,
          title: document.title,
          hasVideo: !!v,
          videoClasses: v ? v.className : null,
          videoSrc: v ? (v.src || v.currentSrc) : null,
          readyState: v ? v.readyState : null,
          currentTime: v ? v.currentTime : null,
          allVideosCount: document.querySelectorAll('video').length,
          allIframes: Array.from(document.querySelectorAll('iframe')).map(i => i.src)
        };
      })()`,
      returnByValue: true
    });

    console.log('Page DOM check:', JSON.stringify(state, null, 2));
    ws.close();
  };
}

main().catch(console.error);
