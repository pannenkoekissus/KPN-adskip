// scratch/check_current_url.js
async function main() {
  const res = await fetch('http://localhost:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.id === '7BCDE5C6517F99DE284D777D1EED2D07');
  console.log('Target page:', page ? { title: page.title, url: page.url } : 'Not found');
}
main();
