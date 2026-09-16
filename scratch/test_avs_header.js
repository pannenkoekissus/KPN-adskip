// scratch/test_avs_header.js
async function main() {
  const res = await fetch('https://api-avs67.tv.prod.itvavs.prod.aws.kpn.com/000002/1.5/A/nld/pctv/kpn/TRAY/LIVECHANNELS?orderBy=orderId&sortOrder=asc&from=0&to=30', {
    headers: {
      'AVSSite': 'http://www.itvonline.nl'
    }
  });
  const data = await res.json();
  const channels = (data.resultObj?.containers?.[0]?.elements || []).map(e => ({
    id: e.id,
    name: e.metadata?.channelName,
    contentOptions: e.metadata?.contentOptions
  }));
  console.log('Channels found with AVSSite:', channels);
}
main().catch(console.error);
