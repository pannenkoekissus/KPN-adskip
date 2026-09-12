// scratch/inspect_all_contentful.js
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
        const res = await fetch('https://cdn.contentful.com/spaces/p895x3dv9duy/environments/master/entries?limit=500&include=10&metadata.tags.sys.id[all]=kpn,web&sys.contentType.sys.id[in]=button,channelKeywords,dialog,error,filter,page,setting,settingGroup,streamingQuality,update,updateType,upsell&locale=nl-NL');
        const json = await res.json();
        
        const relevant = [];
        for (const item of json.items || []) {
          const str = JSON.stringify(item.fields);
          if (/doorspoelen|reclame|commercial|spoel|trickplay|blokkeer/i.test(str)) {
            relevant.push(item);
          }
        }
        return relevant;
      })()`,
      awaitPromise: true,
      returnByValue: true
    });

    console.log('Relevant 2:', JSON.stringify(labels, null, 2));
    ws.close();
  };
}

main().catch(console.error);
