// scratch/inspect_renze_buttons.js
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

    const check = await send('Runtime.evaluate', {
      expression: `(() => {
        const btns = Array.from(document.querySelectorAll('button, a')).map(b => ({
          tag: b.tagName,
          text: b.textContent.trim(),
          className: b.className,
          dataT: b.getAttribute('data-t')
        }));
        const video = document.querySelector('video');
        return {
          title: document.title,
          hasVideo: !!video,
          btns: btns.filter(b => b.text.length > 0).slice(0, 15)
        };
      })()`,
      returnByValue: true
    });

    console.log('Renze page buttons:', JSON.stringify(check, null, 2));
    ws.close();
  };
}

main().catch(console.error);
