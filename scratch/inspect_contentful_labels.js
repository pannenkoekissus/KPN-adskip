// scratch/inspect_contentful_labels.js
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

    const labels = await send('Runtime.evaluate', {
      expression: `(async () => {
        // Fetch contentful player labels
        const res = await fetch('https://cdn.contentful.com/spaces/p895x3dv9duy/environments/master/entries?limit=500&include=10&metadata.tags.sys.id[all]=kpn,web&sys.contentType.sys.id[in]=detailPageLabels,dshConfig,generalConfig,generalLabels,generalStyle,login,migration,parentalControl,playerConfig,playerLabels,profile,recording,search,serviceMessage,smartBanner&locale=nl-NL');
        const json = await res.json();
        
        // Find fields mentioning doorspoelen, reclame, ad, trickplay
        const relevant = [];
        for (const item of json.items || []) {
          for (const key in item.fields) {
            const val = JSON.stringify(item.fields[key]);
            if (/doorspoelen|reclame|commercial|spoel|trickplay|blokkeer/i.test(val)) {
              relevant.push({ contentType: item.sys.contentType.sys.id, field: key, val: item.fields[key] });
            }
          }
        }
        return relevant;
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Relevant Contentful labels:', JSON.stringify(labels, null, 2));
    ws.close();
  };
}

main().catch(console.error);
