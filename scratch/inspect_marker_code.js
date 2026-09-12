// scratch/inspect_marker_code.js
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
        const controls = ui?.getControls();
        const player = controls?.getPlayer();

        // Let's inspect controls members and methods
        const controlKeys = controls ? Object.keys(controls) : [];
        const playerKeys = player ? Object.keys(player) : [];

        // Check timeline or manifest info on player
        let manifest = null;
        if (player?.getManifest) {
          const m = player.getManifest();
          manifest = {
            periodsCount: m?.periods?.length,
            periodStarts: m?.periods?.map(p => p.startTime),
            variantsCount: m?.periods?.[0]?.variants?.length
          };
        }

        // Check if seek bar has custom methods or listeners
        const seekBar = document.querySelector('.shaka-seek-bar');
        const rangeContainer = document.querySelector('.shaka-seek-bar-container');

        return {
          controlKeys,
          manifest,
          playerMediaElement: !!player?.getMediaElement(),
          playRate: player?.getPlaybackRate(),
          isLive: player?.isLive()
        };
      })()`,
      returnByValue: true
    });

    console.log('Player & Controls:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
