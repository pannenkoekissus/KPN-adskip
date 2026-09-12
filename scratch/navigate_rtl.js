// scratch/navigate_rtl.js
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

    console.log('Navigating to TV Gids...');
    await send('Page.navigate', { url: 'https://tv.kpn.com/tv-gids' });
    await new Promise(r => setTimeout(r, 4000));

    // Inspect channels and programs in TV Gids
    const info = await send('Runtime.evaluate', {
      expression: `(() => {
        // Find elements mentioning RTL
        const all = Array.from(document.querySelectorAll('*'));
        const rtlEls = all.filter(el => {
          const t = el.textContent || '';
          return (t.includes('RTL 4') || t.includes('RTL 5') || t.includes('RTL 7') || t.includes('RTL 8') || t.includes('RTL')) && el.children.length === 0;
        }).map(el => ({
          tag: el.tagName,
          text: el.textContent.trim(),
          className: el.className,
          parentTag: el.parentElement?.tagName,
          parentClass: el.parentElement?.className
        })).slice(0, 15);

        return {
          title: document.title,
          url: window.location.href,
          rtlMatches: rtlEls,
          buttonTexts: Array.from(document.querySelectorAll('button, a')).map(b => b.textContent.trim()).filter(Boolean).slice(0, 20)
        };
      })()`,
      returnByValue: true
    });

    console.log('TV Gids inspection:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
