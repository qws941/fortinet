export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/api/health') {
      return new Response(JSON.stringify({
        status: 'healthy',
        service: 'fortinet-nextrade',
        deployment: 'cloudflare-workers',
        timestamp: new Date().toISOString()
      }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response('FortiGate Nextrade - Cloudflare Workers', {
      headers: { 'Content-Type': 'text/plain' }
    });
  }
};
