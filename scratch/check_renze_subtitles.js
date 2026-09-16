// scratch/check_renze_subtitles.js
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

    const subInfo = await send('Runtime.evaluate', {
      expression: `(async () => {
        const p = window._player;
        if (!p) return 'No player';

        const tracks = p.getTextTracks();
        const nl = tracks.find(t => t.language === 'nl');
        if (!nl) return 'No NL track';

        // Select the text track and enable visibility
        p.selectTextTrack(nl);
        p.setTextTrackVisibility(true);

        await new Promise(r => setTimeout(r, 2000));

        const video = document.querySelector('video');
        const tt = Array.from(video.textTracks || []);
        return {
          tracksCount: tracks.length,
          activeTextTracks: tt.map(t => ({
            label: t.label,
            kind: t.kind,
            cuesCount: t.cues ? t.cues.length : 0,
            cues: t.cues ? Array.from(t.cues).slice(0, 10).map(c => ({ start: c.startTime, end: c.endTime, text: c.text })) : []
          }))
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Renze subtitles:', JSON.stringify(subInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
