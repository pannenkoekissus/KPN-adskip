// scratch/check_current_state.js
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
        const video = document.querySelector('video');
        const start = document.querySelector('.shaka_seek-bar-marker_start');
        const end = document.querySelector('.shaka_seek-bar-marker_end');

        let startPct = null;
        if (start && start.style.left) {
          startPct = parseFloat(start.style.left);
        }
        let endPct = null;
        if (end && end.style.right) {
          endPct = 100 - parseFloat(end.style.right);
        }

        const duration = video ? video.duration : null;
        const current = video ? video.currentTime : null;

        const startTime = (startPct !== null && duration) ? (startPct / 100) * duration : null;
        const endTime = (endPct !== null && duration) ? (endPct / 100) * duration : null;

        const isCurrentlyInAd = (current !== null && startTime !== null && endTime !== null) 
          ? (current >= startTime - 0.5 && current < endTime) 
          : false;

        // Check if there is any text like "Reclame", or ad-counter
        const adCounter = document.querySelector('.shaka-ad-counter, .shaka-ad-position, .shaka-ad-controls');
        const allText = document.body.innerText;
        const adMentions = ['Reclame', 'Advertentie', 'Ad 1', 'Ad '].filter(m => allText.includes(m));

        return {
          current,
          duration,
          paused: video ? video.paused : null,
          startPct,
          endPct,
          startTime,
          endTime,
          isCurrentlyInAd,
          adCounterText: adCounter ? adCounter.textContent.trim() : null,
          adCounterHidden: adCounter ? adCounter.classList.contains('shaka-hidden') : null,
          adMentions
        };
      })()`,
      returnByValue: true
    });

    console.log('Current ad check:', JSON.stringify(info, null, 2));
    ws.close();
  };
}

main().catch(console.error);
