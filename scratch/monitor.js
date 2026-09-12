// scratch/monitor.js
// Continuously monitors tv.kpn.com for video playback, player objects, and ad signals
const fs = require('fs');

async function main() {
  const res = await fetch('http://localhost:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.type === 'page' && t.url.includes('tv.kpn.com'));
  if (!page) {
    console.error('KPN tab not found!');
    return;
  }
  console.log('Connecting to KPN tab:', page.title, page.url);
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

    // Enable console and network
    await send('Console.enable');
    await send('Network.enable');

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.method === 'Console.messageAdded') {
          console.log('[BROWSER CONSOLE]', msg.params.message.text);
        }
        if (msg.method === 'Network.requestWillBeSent') {
          const url = msg.params.request.url;
          if (/ad|vast|vmap|scte|cue|emp|playback|timeline|commercial|reclame/i.test(url) && !url.includes('google-analytics') && !url.includes('sentry')) {
            console.log('[NETWORK INTERESTING]', msg.params.request.method, url.substring(0, 150));
          }
        }
      } catch (e) {}
    };

    // Inject observer & hooks into page
    const hookRes = await send('Runtime.evaluate', {
      expression: `(() => {
        if (window.__ad_monitor_installed) return 'Already installed';
        window.__ad_monitor_installed = true;

        console.log('🚀 AD MONITOR INSTALLED IN PAGE');

        // Hook Shaka Player if instantiated
        if (window.shaka && window.shaka.Player) {
          const originalInit = window.shaka.Player;
          console.log('Shaka player class detected');
        }

        // Intercept fetch & XHR to detect ad manifest / timeline / VAST
        const origFetch = window.fetch;
        window.fetch = async function(...args) {
          const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
          const res = await origFetch.apply(this, args);
          try {
            if (/ad|vast|scte|timeline|emp|cue/i.test(url) && !url.includes('analytics')) {
              const clone = res.clone();
              clone.text().then(text => {
                if (text.includes('Ad') || text.includes('ad') || text.includes('Break') || text.includes('cue')) {
                  console.log('[FETCH AD-DATA]', url.substring(0, 100), 'Snippet:', text.substring(0, 200));
                }
              }).catch(() => {});
            }
          } catch(e) {}
          return res;
        };

        // Track Video elements & ad UI
        setInterval(() => {
          const video = document.querySelector('video');
          if (video) {
            const hasClassOrAttr = Array.from(video.classList).join(' ');
            // Check for ad markers / text in DOM
            const bodyText = document.body.innerText;
            const adKeywords = ['Reclame', 'Advertentie', 'Reclameblok', 'Reclame doorspoelen'];
            const foundKeywords = adKeywords.filter(kw => bodyText.includes(kw));

            // Check progress bar elements
            const cuePoints = document.querySelectorAll('[class*="ad"], [class*="cue"], [class*="marker"], [class*="break"]');
            
            if (foundKeywords.length > 0 || cuePoints.length > 0) {
              console.log('[PAGE MONITOR] Video active at ' + Math.round(video.currentTime) + '/' + Math.round(video.duration) + 's. Keywords:', foundKeywords, 'CueElements:', cuePoints.length);
            }
          }
        }, 1500);

        return 'Installed hook successfully';
      })()`,
      returnByValue: true
    });

    console.log('Hook result:', hookRes);
  };
}

main().catch(console.error);
