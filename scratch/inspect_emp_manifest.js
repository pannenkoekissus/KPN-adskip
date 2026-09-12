// scratch/inspect_emp_manifest.js
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
        const container = document.querySelector('.shaka-video-container');
        const ui = container?.ui;
        const player = ui?.getControls()?.getPlayer();
        const video = document.querySelector('video');

        const details = {
          assetUrl: player?.getAssetUri ? player.getAssetUri() : null,
          manifestUri: player?.getManifestUri ? player.getManifestUri() : null,
          currentTime: video ? video.currentTime : null,
          duration: video ? video.duration : null,
        };

        // Check EMP player instance or any window/document global related to ads/emp
        details.empGlobals = Object.keys(window).filter(k => /emp|player|ad|kpn/i.test(k));

        // Check if player has ad cues or timeline regions
        if (player) {
          // Check text tracks / metadata tracks / event listeners
          details.textTracks = Array.from(video.textTracks || []).map(t => ({
            kind: t.kind,
            label: t.label,
            cuesCount: t.cues ? t.cues.length : 0,
            cues: t.cues ? Array.from(t.cues).map(c => ({ start: c.startTime, end: c.endTime, text: c.text })) : []
          }));
        }

        // Check Shaka AdManager
        if (player?.getAdManager) {
          const am = player.getAdManager();
          details.adManagerMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(am));
        }

        return details;
      })()`,
      returnByValue: true
    });

    console.log('Manifest & Tracks:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
