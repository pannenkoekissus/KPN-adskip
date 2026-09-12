// scratch/inspect_video_currenttime.js
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

    const descInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        const video = document.querySelector('video');
        if (!video) return 'No video';

        const ownDesc = Object.getOwnPropertyDescriptor(video, 'currentTime');
        const protoDesc = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime');

        return {
          hasOwnDescriptor: !!ownDesc,
          ownDesc: ownDesc ? {
            hasGet: !!ownDesc.get,
            hasSet: !!ownDesc.set,
            configurable: ownDesc.configurable
          } : null,
          protoDesc: {
            hasGet: !!protoDesc.get,
            hasSet: !!protoDesc.set,
            configurable: protoDesc.configurable
          }
        };
      })()`,
      returnByValue: true
    });

    console.log('currentTime descriptor:', JSON.stringify(descInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
