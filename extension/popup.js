document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('autoSkipPreRoll');

  chrome.storage.sync.get(['autoSkipPreRoll'], (result) => {
    if (result.autoSkipPreRoll !== undefined) {
      toggle.checked = result.autoSkipPreRoll;
    }
  });

  toggle.addEventListener('change', () => {
    chrome.storage.sync.set({ autoSkipPreRoll: toggle.checked });
  });
});
