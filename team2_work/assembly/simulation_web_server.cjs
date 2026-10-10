// Simulation assembly: existing static frontend plus unchanged optional candidate routing.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(process.env.UKAI_DIST_ROOT || path.join(__dirname, '..', 'frontend', 'dist'));
const port = Number(process.env.UKAI_WEB_PORT || 5174);
const apiPort = Number(process.env.UKAI_API_PORT || 8766);
const candidatePort = process.env.UKAI_CANDIDATE_PORT ? Number(process.env.UKAI_CANDIDATE_PORT) : null;
for (const value of [port, apiPort, ...(candidatePort === null ? [] : [candidatePort])]) {
  if (!Number.isInteger(value) || value < 1 || value > 65535) throw new Error('Invalid local service port');
}
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8',
  '.css':'text/css; charset=utf-8','.json':'application/json','.svg':'image/svg+xml',
  '.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2','.wasm':'application/wasm'};
const server = http.createServer((req, res) => {
  if (req.url === '/__ukai_instance') {
    res.writeHead(200, {'Content-Type':'application/json','Cache-Control':'no-store'});
    return res.end(JSON.stringify({instance:process.env.UKAI_INSTANCE}));
  }
  if (req.url.startsWith('/api/')) {
    const pathname = new URL(req.url, 'http://127.0.0.1').pathname;
    const candidate = pathname === '/api/v1/candidates' || pathname.startsWith('/api/v1/candidates/');
    const target = candidate && candidatePort !== null ? candidatePort : apiPort;
    const headers = {...req.headers, host:`127.0.0.1:${target}`};
    delete headers.connection;
    const outgoing = http.request({hostname:'127.0.0.1',port:target,path:req.url,method:req.method,headers}, upstream => {
      res.writeHead(upstream.statusCode, upstream.headers);
      upstream.on('error', () => res.destroy());
      upstream.pipe(res);
      res.on('close', () => upstream.destroy());
    });
    outgoing.on('error', () => {
      if (!res.headersSent) res.writeHead(503, {'Content-Type':'application/problem+json','Cache-Control':'no-store'});
      res.end(JSON.stringify({detail:candidate ? 'The local candidate service is not available.' : 'The local API is not available.'}));
    });
    outgoing.setTimeout(30000, () => outgoing.destroy());
    req.on('aborted', () => outgoing.destroy());
    return req.pipe(outgoing);
  }
  if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405); return res.end(); }
  let key;
  try { key = decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname); }
  catch { res.writeHead(400); return res.end(); }
  if (key.includes('\\') || key.includes('\0')) { res.writeHead(400); return res.end(); }
  let file = path.resolve(root, '.'+key);
  if (file !== root && !file.startsWith(root+path.sep)) { res.writeHead(404); return res.end(); }
  if (file === root) file = path.join(root,'index.html');
  fs.stat(file, (error, stat) => {
    if (error || !stat.isFile()) {
      if (path.extname(key)) { res.writeHead(404); return res.end(); }
      file = path.join(root,'index.html');
    }
    fs.stat(file, (second, final) => {
      if (second || !final.isFile()) { res.writeHead(404); return res.end(); }
      res.writeHead(200, {'Content-Type':types[path.extname(file)] || 'application/octet-stream',
        'Content-Length':final.size,'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'});
      if (req.method === 'HEAD') return res.end();
      const stream = fs.createReadStream(file);
      stream.on('error', () => res.destroy());
      res.on('close', () => stream.destroy());
      stream.pipe(res);
    });
  });
});
server.on('error', error => { console.error('Local frontend could not bind:',error.code); process.exit(1); });
server.listen(port,'127.0.0.1',() => console.log(`SSD frontend ready: http://127.0.0.1:${port}`));
