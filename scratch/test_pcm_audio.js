// scratch/test_pcm_audio.js
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

    const testAudio = await send('Runtime.evaluate', {
      expression: `(async () => {
        const video = document.querySelector('video');
        if (!video) return 'No video';

        const ac = new (window.AudioContext || window.webkitAudioContext)();
        const src = ac.createMediaElementSource(video);
        const processor = ac.createScriptProcessor(2048, 1, 1);

        let capturedSamples = [];
        let maxVolume = 0;

        await new Promise(resolve => {
          processor.onaudioprocess = (e) => {
            const input = e.inputBuffer.getChannelData(0);
            for (let i = 0; i < input.length; i++) {
              const abs = Math.abs(input[i]);
              if (abs > maxVolume) maxVolume = abs;
            }
            capturedSamples.push(maxVolume);
            if (capturedSamples.length >= 10) {
              resolve();
            }
          };
          src.connect(processor);
          processor.connect(ac.destination);
        });

        src.disconnect();
        processor.disconnect();

        return {
          maxVolume,
          samplesCount: capturedSamples.length,
          sampleRate: ac.sampleRate,
          firstSamples: capturedSamples.slice(0, 5)
        };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('PCM Audio test result:', JSON.stringify(testAudio, null, 2));
    ws.close();
  };
}

main().catch(console.error);
