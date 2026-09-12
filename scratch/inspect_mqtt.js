// scratch/inspect_mqtt.js
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

    const mqttInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        const paho = window.Paho;
        // Search window for mqtt client
        let mqttClient = null;
        for (let k in window) {
          if (window[k] && window[k].isConnected && typeof window[k].isConnected === 'function') {
            mqttClient = { key: k, connected: window[k].isConnected() };
          }
        }
        return {
          hasPaho: !!paho,
          mqttClient
        };
      })()`,
      returnByValue: true
    });

    console.log('MQTT info:', JSON.stringify(mqttInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
