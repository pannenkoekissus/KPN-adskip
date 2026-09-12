// scratch/inspect_ad_elements.js
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

    const info = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        const cueEls = Array.from(document.querySelectorAll('[class*="ad"], [class*="cue"], [class*="marker"], [class*="break"]')).map(el => ({
          tag: el.tagName,
          className: el.className,
          style: el.getAttribute('style'),
          text: el.textContent.trim(),
          rect: el.getBoundingClientRect()
        }));

        // Search for Shaka player instance on window or DOM elements
        let shakaPlayer = null;
        if (window.shaka) {
          // Check video element for attached player or search Vue/React/DOM properties
          for (let k in video) {
            if (k.startsWith('__vue') || k.startsWith('__react') || k.includes('player') || k.includes('shaka')) {
              // candidate
            }
          }
        }

        // Check progress bar / seek bar in DOM
        const progressBars = Array.from(document.querySelectorAll('[role="slider"], [class*="progress"], [class*="seek"], [class*="timeline"]')).map(p => ({
          tag: p.tagName,
          className: p.className,
          ariaValuenow: p.getAttribute('aria-valuenow'),
          ariaValuemax: p.getAttribute('aria-valuemax'),
          childrenClasses: Array.from(p.children).map(c => c.className + ' | ' + c.getAttribute('style'))
        }));

        // Check player overlays or banners
        const overlays = Array.from(document.querySelectorAll('[class*="overlay"], [class*="message"], [class*="toast"], [class*="alert"]')).map(o => ({
          className: o.className,
          text: o.textContent.trim()
        })).filter(o => o.text.length > 0);

        return {
          currentTime: video ? video.currentTime : null,
          duration: video ? video.duration : null,
          paused: video ? video.paused : null,
          cueElements: cueEls.slice(0, 25),
          progressBars,
          overlays
        };
      })()`,
      returnByValue: true
    });

    console.log('Ad Elements & State:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
