// scratch/inspect_renze_player.js
async function main() {
  const res = await fetch('http://localhost:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.id === '7BCDE5C6517F99DE284D777D1EED2D07' || (t.type === 'page' && t.url.includes('tv.kpn.com')));
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

    const details = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        const markers = Array.from(document.querySelectorAll('.shaka_seek-bar-marker')).map(m => ({
          className: m.className,
          style: m.getAttribute('style')
        }));

        const p = window._player;
        const uri = p?.getAssetUri ? p.getAssetUri() : null;

        // Check text tracks
        const textTracks = Array.from(video.textTracks || []).map(t => ({
          kind: t.kind,
          label: t.label,
          mode: t.mode,
          cuesCount: t.cues ? t.cues.length : 0
        }));

        return {
          currentTime: video.currentTime,
          duration: video.duration,
          markers,
          uri,
          textTracks
        };
      })()`,
      returnByValue: true
    });

    console.log('Renze player state:', JSON.stringify(details, null, 2));
    ws.close();
  };
}

main().catch(console.error);
