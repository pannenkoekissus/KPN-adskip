// scratch/inspect_react_fiber.js
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

    const fiberInfo = await send('Runtime.evaluate', {
      expression: `(() => {
        // Find fiber root from #app or video
        const el = document.querySelector('video') || document.querySelector('#app');
        let fiber = null;
        for (let k in el) {
          if (k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')) {
            fiber = el[k];
            break;
          }
        }
        if (!fiber) return 'No fiber';

        // Traverse up to find state or memoizedState / props with programDetails
        let cur = fiber;
        let foundDetails = null;
        let foundSeekLimit = null;
        while (cur) {
          if (cur.memoizedProps?.item?.title || cur.memoizedProps?.programDetails) {
            foundDetails = cur.memoizedProps;
          }
          if (cur.memoizedProps?.seekLimitRange) {
            foundSeekLimit = cur.memoizedProps.seekLimitRange;
          }
          cur = cur.return;
        }

        return {
          foundSeekLimit,
          item: foundDetails?.item ? {
            title: foundDetails.item.title,
            duration: foundDetails.item.duration,
            contentOptions: foundDetails.item.contentOptions,
            channel: foundDetails.item.channel
          } : null
        };
      })()`,
      returnByValue: true
    });

    console.log('Fiber info:', JSON.stringify(fiberInfo, null, 2));
    ws.close();
  };
}

main().catch(console.error);
