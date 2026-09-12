// scratch/inspect_shaka_adbreaks.js
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

    const adBreakInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        const container = document.querySelector('.shaka-video-container');
        const ui = container?.ui;
        const controls = ui?.getControls();
        const player = controls?.getPlayer();

        // Check controls for seek bar component
        // Shaka stores UI components
        let seekBarComponent = null;
        if (controls) {
          for (let key in controls) {
            const val = controls[key];
            if (val && typeof val === 'object') {
              // check if it has seekBar or adBreaks or player
              if (val.seekBar || (val.player && val.m && val.m.seekBarColors)) {
                seekBarComponent = { key, valKeys: Object.keys(val) };
              }
            }
          }
        }

        // Search recursively inside controls for any array containing start/end or adBreaks
        function findAdBreaks(obj, depth = 0, path = '') {
          if (!obj || depth > 4) return null;
          for (let k in obj) {
            try {
              const item = obj[k];
              if (Array.isArray(item) && item.length > 0) {
                if (item[0] && (typeof item[0].start === 'number' || typeof item[0].startTime === 'number' || item[0].isAd !== undefined)) {
                  return { path: path + '.' + k, item };
                }
              }
              if (item && typeof item === 'object' && !Array.isArray(item) && !k.startsWith('parent') && k !== 'window' && k !== 'document') {
                const res = findAdBreaks(item, depth + 1, path + '.' + k);
                if (res) return res;
              }
            } catch(e) {}
          }
          return null;
        }

        const foundInControls = findAdBreaks(controls, 0, 'controls');
        const foundInPlayer = findAdBreaks(player, 0, 'player');
        const foundInUI = findAdBreaks(ui, 0, 'ui');

        return {
          foundInControls,
          foundInPlayer,
          foundInUI,
          seekBarComponent
        };
      })()`,
      returnByValue: true
    });

    console.log('AdBreak Search:', JSON.stringify(adBreakInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
