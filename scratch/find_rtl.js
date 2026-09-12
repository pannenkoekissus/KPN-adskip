// scratch/find_rtl.js
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
        // Find any element mentioning RTL 4
        const all = Array.from(document.querySelectorAll('*'));
        const rtlNodes = all.filter(e => {
          const text = e.getAttribute('aria-label') || e.alt || (e.children.length === 0 ? e.textContent : '');
          return text && /RTL\s*4/i.test(text);
        });

        const results = rtlNodes.map(node => {
          // Find container or row
          let p = node;
          while (p && p !== document.body && !p.getAttribute('role')?.includes('row') && !p.className?.includes('row') && !p.className?.includes('channel')) {
            p = p.parentElement;
          }
          return {
            text: node.textContent.trim(),
            aria: node.getAttribute('aria-label'),
            alt: node.alt,
            parentClass: p ? p.className : null,
            parentRole: p ? p.getAttribute('role') : null,
            parentHTML: p ? p.innerHTML.substring(0, 300) : null
          };
        });

        // Also look for program titles in TV guide for RTL 4
        return {
          rtlNodesCount: rtlNodes.length,
          results: results.slice(0, 5)
        };
      })()`,
      returnByValue: true
    });

    console.log('RTL Search:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
