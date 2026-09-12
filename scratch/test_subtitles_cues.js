// scratch/test_subtitles_cues.js
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

    const testSub = await send('Runtime.evaluate', {
      expression: `(async () => {
        const p = window._player;
        if (!p) return 'No player';

        const tracks = p.getTextTracks();
        const nlTrack = tracks.find(t => t.language === 'nl');
        if (!nlTrack) return { tracksCount: tracks.length, tracks };

        p.selectTextTrack(nlTrack);
        p.setTextTrackVisibility(true);

        await new Promise(r => setTimeout(r, 2000));

        const video = document.querySelector('video');
        const activeTextTracks = Array.from(video.textTracks || []);
        const activeCues = activeTextTracks.map(t => ({
          kind: t.kind,
          label: t.label,
          cuesCount: t.cues ? t.cues.length : 0,
          sampleCues: t.cues ? Array.from(t.cues).slice(0, 5).map(c => ({ start: c.startTime, end: c.endTime, text: c.text })) : []
        }));

        return {
          nlTrack,
          activeCues
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Subtitles test:', JSON.stringify(testSub, null, 2));
    ws.close();
  };
}

main().catch(console.error);
