// scratch/inspect_emp_api_more.js
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

    const resInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        // Inspect window.Agama
        const agama = window.Agama;
        
        // Inspect window.emp / EMP client
        // Check if there are any global objects or properties on window
        const interesting = [];
        for (const k in window) {
          if (/ad|commercial|break|cue|segment|chapter/i.test(k)) {
            interesting.push(k);
          }
        }

        // Check if video textTracks has any active tracks or cues
        const video = document.querySelector('video');
        const tt = video ? Array.from(video.textTracks).map(t => ({
          kind: t.kind,
          label: t.label,
          mode: t.mode,
          cuesLength: t.cues ? t.cues.length : 0
        })) : [];

        return {
          interesting,
          textTracks: tt
        };
      })()`,
      returnByValue: true
    });

    console.log('Agama & Tracks:', JSON.stringify(resInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
