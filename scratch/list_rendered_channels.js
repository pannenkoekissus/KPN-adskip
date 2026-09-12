// scratch/list_rendered_channels.js
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
        // look for img or icons with channel names
        const imgs = Array.from(document.querySelectorAll('img')).map(i => ({ alt: i.alt, src: i.src })).filter(i => i.alt || i.src.includes('channel') || i.src.includes('logo'));
        // look for text that might be channels
        const ariaLabels = Array.from(document.querySelectorAll('[aria-label]')).map(el => el.getAttribute('aria-label'));
        return {
          imgs: imgs.slice(0, 20),
          ariaLabels: ariaLabels.filter(a => a.toLowerCase().includes('npo') || a.toLowerCase().includes('rtl') || a.toLowerCase().includes('zender') || a.toLowerCase().includes('kijk')).slice(0, 30)
        };
      })()`,
      returnByValue: true
    });

    console.log('Rendered channels:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
