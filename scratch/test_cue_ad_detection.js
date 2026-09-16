// scratch/test_cue_ad_detection.js
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

    const cueGaps = await send('Runtime.evaluate', {
      expression: `(async () => {
        const video = document.querySelector('video');
        if (!video) return 'No video';

        // Check text tracks
        const tt = Array.from(video.textTracks || []);
        const subTrack = tt.find(t => t.kind === 'subtitles') || tt[0];
        if (!subTrack) return 'No subtitle track';

        subTrack.mode = 'hidden';
        const cues = Array.from(subTrack.cues || []);

        // Find gaps > 120 seconds between consecutive cues
        const adBreaks = [];
        for (let i = 0; i < cues.length - 1; i++) {
          const gap = cues[i + 1].startTime - cues[i].endTime;
          if (gap > 120) {
            adBreaks.push({
              adStart: cues[i].endTime,
              adEnd: cues[i + 1].startTime,
              gapDurationSeconds: Math.round(gap),
              lastDialogueBeforeAd: cues[i].text,
              firstDialogueAfterAd: cues[i + 1].text
            });
          }
        }

        return {
          totalCues: cues.length,
          detectedAdBreaks: adBreaks
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Detected Ad Breaks via Cues:', JSON.stringify(cueGaps, null, 2));
    ws.close();
  };
}

main().catch(console.error);
