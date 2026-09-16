// scratch/inspect_renze.js
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

    const state = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        const p = window._player;
        const textTracks = p ? p.getTextTracks() : [];
        const videoTracks = video ? Array.from(video.textTracks) : [];

        // Check if there are cues loaded in any text track
        const tracksInfo = videoTracks.map(t => ({
          kind: t.kind,
          label: t.label,
          mode: t.mode,
          cuesCount: t.cues ? t.cues.length : 0,
          sampleCues: t.cues ? Array.from(t.cues).slice(0, 10).map(c => ({ start: c.startTime, end: c.endTime, text: c.text })) : []
        }));

        // Seekbar markers
        const markers = Array.from(document.querySelectorAll('.shaka_seek-bar-marker')).map(m => ({
          className: m.className,
          style: m.getAttribute('style')
        }));

        return {
          title: document.title,
          currentTime: video ? video.currentTime : null,
          duration: video ? video.duration : null,
          paused: video ? video.paused : null,
          shakaTextTracks: textTracks.map(t => ({ id: t.id, lang: t.language, type: t.type })),
          tracksInfo,
          markers
        };
      })()`,
      returnByValue: true
    });

    console.log('Renze live state:', JSON.stringify(state, null, 2));
    ws.close();
  };
}

main().catch(console.error);
