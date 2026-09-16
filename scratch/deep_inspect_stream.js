// scratch/deep_inspect_stream.js
const fs = require('fs');

async function main() {
  const res = await fetch('http://127.0.0.1:9222/json');
  const targets = await res.json();
  const page = targets.find(t => t.type === 'page' && t.url.includes('tv.kpn.com'));
  if (!page) {
    console.log('No KPN page found');
    return;
  }
  console.log('Attaching to:', page.title, page.url);
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

    // Inspect the player object in the page
    const playerInspection = await send('Runtime.evaluate', {
      expression: `(() => {
        const v = document.querySelector('video');
        // Let's find shaka player instance
        let shakaPlayer = null;
        let emp = null;
        // Search window for shaka or emp
        for (let k in window) {
          try {
            if (window[k] && window[k].getManifest) shakaPlayer = window[k];
            if (window[k] && window[k].emp) emp = window[k].emp;
          } catch(e) {}
        }

        // Also check if video or shaka UI has controls
        const uiContainer = document.querySelector('.shaka-video-container') || document.querySelector('[data-shaka-player-container]');
        let shakaUi = null;
        if (uiContainer && uiContainer['ui']) shakaUi = uiContainer['ui'];

        // Let's inspect React/Preact fiber on the player container or video
        let fiber = null;
        let cur = v;
        while (cur && !fiber) {
          for (let k in cur) {
            if (k.startsWith('__preact') || k.startsWith('__reactFiber')) {
              fiber = cur[k];
              break;
            }
          }
          cur = cur.parentElement;
        }

        // Inspect manifest
        let manifest = null;
        if (shakaPlayer) {
          try {
            manifest = shakaPlayer.getManifest();
          } catch(e) {}
        }

        return {
          hasVideo: !!v,
          videoTime: v ? v.currentTime : null,
          videoDuration: v ? v.duration : null,
          videoSrc: v ? v.src : null,
          hasShakaPlayer: !!shakaPlayer,
          manifestPeriodsCount: manifest ? manifest.periods?.length : null,
          manifestTextStreams: manifest ? manifest.periods?.[0]?.textStreams?.length : null
        };
      })()`,
      returnByValue: true
    });

    console.log('Player inspection:', JSON.stringify(playerInspection, null, 2));

    ws.close();
  };
}

main().catch(console.error);
