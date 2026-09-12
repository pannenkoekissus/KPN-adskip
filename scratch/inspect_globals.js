// scratch/inspect_globals.js
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

    const evalRes = await send('Runtime.evaluate', {
      expression: `({
        globalKeys: Object.keys(window).filter(k => !k.startsWith('webkit') && !k.startsWith('on')),
        hasPlayer: !!window.player || !!window.shaka || !!window.videojs || !!window.theoplayer || !!window.bitmovin,
        navLinks: Array.from(document.querySelectorAll('a, button, nav')).map(e => ({
          text: e.textContent.trim(),
          href: e.href || e.getAttribute('to') || null,
          role: e.getAttribute('role')
        })).filter(x => x.text.length > 0 && x.text.length < 30).slice(0, 30)
      })`,
      returnByValue: true
    });
    console.log('Eval result:', JSON.stringify(evalRes, null, 2));
    ws.close();
  };
}

main().catch(console.error);
