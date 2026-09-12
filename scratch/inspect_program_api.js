// scratch/inspect_program_api.js
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

    const apiDetails = await send('Runtime.evaluate', {
      expression: `(async () => {
        // Let's check window.__store or Vuex or Pinia or Redux or Angular or whatever state management KPN TV uses
        const vueApp = document.querySelector('#app')?.__vue_app__ || document.querySelector('#app')?._vnode?.component;
        
        // Find state in DOM or window
        let stateObj = null;
        if (window.__INITIAL_STATE__) stateObj = window.__INITIAL_STATE__;

        // Let's check the video url response by fetching the video url again or checking sessionStorage/localStorage
        const storageKeys = Object.keys(sessionStorage).concat(Object.keys(localStorage));

        return {
          storageKeys: storageKeys.filter(k => /emp|player|stream|video|pvr|ad/i.test(k)),
          vueProps: vueApp ? Object.keys(vueApp) : null
        };
      })()`,
      returnByValue: true
    });

    console.log('API details:', JSON.stringify(apiDetails, null, 2));
    ws.close();
  };
}

main().catch(console.error);
