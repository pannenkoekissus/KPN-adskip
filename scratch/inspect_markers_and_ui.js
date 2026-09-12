// scratch/inspect_markers_and_ui.js
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
        const container = document.querySelector('.shaka-video-container');
        
        // Find all elements inside .shaka-range-container
        const rangeContainer = document.querySelector('.shaka-seek-bar-container');
        const allMarkers = Array.from(document.querySelectorAll('.shaka_seek-bar-marker, .shaka-ad-markers, [class*="marker"]')).map(m => ({
          tag: m.tagName,
          className: m.className,
          style: m.getAttribute('style'),
          outerHTML: m.outerHTML
        }));

        // Check if there are multiple start/end marker pairs
        const startMarkers = Array.from(document.querySelectorAll('.shaka_seek-bar-marker_start'));
        const endMarkers = Array.from(document.querySelectorAll('.shaka_seek-bar-marker_end'));

        // Check shaka UI instance on container
        const ui = container ? container.ui : null;
        let player = null;
        if (ui && ui.getControls) {
          player = ui.getControls().getPlayer();
        }

        // Also check if Shaka AdManager exists
        let adManagerInfo = null;
        if (player && player.getAdManager) {
          const adMgr = player.getAdManager();
          adManagerInfo = {
            isAd: adMgr ? (adMgr.isAd ? adMgr.isAd() : null) : null
          };
        }

        return {
          currentTime: video ? video.currentTime : null,
          duration: video ? video.duration : null,
          startMarkers: startMarkers.map(m => m.outerHTML),
          endMarkers: endMarkers.map(m => m.outerHTML),
          allMarkers,
          hasUI: !!ui,
          hasPlayer: !!player,
          adManagerInfo
        };
      })()`,
      returnByValue: true
    });

    console.log('Markers & Player details:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
