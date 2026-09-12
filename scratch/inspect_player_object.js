// scratch/inspect_player_object.js
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
        const am = player?.getAdManager();

        let cuePoints = null;
        if (am && am.getServerSideCuePoints) {
          try {
            cuePoints = am.getServerSideCuePoints();
          } catch (e) {
            cuePoints = 'err: ' + e.message;
          }
        }

        let playerKeys = window._player ? Object.keys(window._player) : [];
        let playerProto = window._player ? Object.getOwnPropertyNames(Object.getPrototypeOf(window._player)) : [];

        // Check window._player properties
        const p = window._player;
        const empDetails = p ? {
          keys: playerKeys,
          proto: playerProto,
          empPlayer: p.empPlayer ? Object.keys(p.empPlayer) : null,
          adInfo: p.ads || p.adManager || p.adBreaks || p.contractRestrictions || p.restrictions || p.metadata
        } : null;

        return {
          cuePoints,
          empDetails
        };
      })()`,
      returnByValue: true
    });

    console.log('Player & Cue points:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
