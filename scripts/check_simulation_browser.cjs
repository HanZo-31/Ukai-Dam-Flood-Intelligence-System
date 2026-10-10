// Offline, isolated rendered-app smoke test. Run after START_SIMULATION is ready.
// Uses installed Chrome and bundled Node 24; no browser or package installation.
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const base = process.env.UKAI_BROWSER_URL || 'http://127.0.0.1:5174';
const out = path.resolve(__dirname, '..', 'simulation_browser_evidence');
const chromePath = process.env.UKAI_TEST_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const report = { started: new Date().toISOString(), url: base, checks: [], screenshots: [],
  browserErrors: [], consoleWarnings: [], networkErrors: [], expectedOfflineErrors: [],
  externalRequests: [], rangeResponses: [] };
let chrome, cdp, profile;
let offlineTestStarted = false;
function recordError(list, item) {
  if (offlineTestStarted && /ERR_INTERNET_DISCONNECTED|ERR_NETWORK_CHANGED/.test(item.message || ''))
    report.expectedOfflineErrors.push(item);
  else list.push(item);
}

class CDP {
  constructor(url) {
    this.socket = new WebSocket(url);
    this.sequence = 0;
    this.pending = new Map();
    this.listeners = new Map();
    this.ready = new Promise((resolve, reject) => {
      this.socket.addEventListener('open', resolve, { once: true });
      this.socket.addEventListener('error', reject, { once: true });
    });
    this.socket.addEventListener('message', event => {
      const data = JSON.parse(event.data);
      if (data.id) {
        const call = this.pending.get(data.id);
        if (!call) return;
        this.pending.delete(data.id);
        clearTimeout(call.timer);
        data.error ? call.reject(new Error(JSON.stringify(data.error))) : call.resolve(data.result);
      } else {
        for (const listener of this.listeners.get(data.method) || []) listener(data.params);
      }
    });
  }
  on(event, listener) {
    this.listeners.set(event, [...(this.listeners.get(event) || []), listener]);
  }
  async send(method, params = {}) {
    await this.ready;
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP timeout: ${method}`));
      }, 30000);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }
  async evaluate(expression) {
    const result = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text + ': ' +
      (result.exceptionDetails.exception?.description || 'page expression failed'));
    return result.result.value;
  }
  close() { this.socket.close(); }
}

async function until(description, operation, timeout = 45000) {
  const started = Date.now();
  let last;
  while (Date.now() - started < timeout) {
    last = await operation();
    if (last) return last;
    await pause(200);
  }
  throw new Error(`Timed out: ${description}; latest result: ${JSON.stringify(last)}`);
}
async function check(name, operation) {
  try {
    const detail = await operation();
    report.checks.push({ name, passed: true, detail });
    console.log(`PASS ${name}`);
    return detail;
  } catch (error) {
    report.checks.push({ name, passed: false, error: error.message });
    console.log(`FAIL ${name}: ${error.message}`);
    await screenshot('failure-' + name).catch(() => {});
    return null;
  }
}
function requireCondition(condition, message) { if (!condition) throw new Error(message); }
async function click(selector, text) {
  await cdp.evaluate(`(() => {
    const elements = [...document.querySelectorAll(${JSON.stringify(selector)})];
    const item = elements.find(el => el.textContent.trim() === ${JSON.stringify(text)});
    if (!item) throw new Error('Control missing: ' + ${JSON.stringify(text)});
    item.click();
  })()`);
  // React must commit before the following observation can describe the new state.
  await pause(100);
}
async function selectScenario(label) {
  await cdp.evaluate(`(() => {
    const item = [...document.querySelectorAll('.scen')].find(el =>
      el.querySelector('strong')?.textContent === ${JSON.stringify(label)});
    if (!item) throw new Error('Scenario missing');
    item.click();
  })()`);
  await pause(100);
  await until('scenario selection', () => cdp.evaluate(`document.querySelector('.scen[aria-pressed="true"] strong')?.textContent === ${JSON.stringify(label)}`));
}
const activeRequests = new Set();
let lastNetworkActivity = Date.now();
async function settled() {
  await until('local network settles', () => activeRequests.size === 0 && Date.now() - lastNetworkActivity > 600, 45000);
  await cdp.evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
}
async function mapsReady(count) {
  await until(`${count} map(s) ready`, async () => {
    const state = await cdp.evaluate(`(() => ({
      states: [...document.querySelectorAll('[data-map-state]')].map(el => el.dataset.mapState),
      errors: [...document.querySelectorAll('.map-overlay.error,.banner')].map(el => el.textContent)
    }))()`);
    if (state.errors.length) throw new Error(state.errors.join('; '));
    return state.states.length === count && state.states.every(value => value === 'ready');
  });
  await settled();
  const canvases = await cdp.evaluate(`([...document.querySelectorAll('.map-host')]).map(host =>
    [...host.querySelectorAll('canvas')].map(canvas => ({ width: canvas.width, height: canvas.height })))`);
  requireCondition(canvases.length === count && canvases.every(list => list.some(c => c.width > 0 && c.height > 0)),
    'A ready map has no rendered canvas');
  return canvases;
}
async function screenshot(name, full = false) {
  if (!cdp) return;
  const safe = name.replace(/[^a-z0-9-]+/gi, '-').toLowerCase();
  const params = { format: 'png', captureBeyondViewport: true };
  if (full) {
    const layout = await cdp.send('Page.getLayoutMetrics');
    params.clip = { x: 0, y: 0, width: layout.cssContentSize.width,
      height: Math.min(layout.cssContentSize.height, 7000), scale: 1 };
  }
  const result = await cdp.send('Page.captureScreenshot', params);
  const file = path.join(out, safe + '.png');
  fs.writeFileSync(file, Buffer.from(result.data, 'base64'));
  report.screenshots.push(file);
}
async function viewport(width, height) {
  await cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1,
    mobile: width < 500, screenWidth: width, screenHeight: height });
  await pause(150);
}

async function main() {
  requireCondition(fs.existsSync(chromePath), `Chrome is missing: ${chromePath}`);
  fs.mkdirSync(out, { recursive: true });
  profile = fs.mkdtempSync(path.join(out, 'chrome-profile-'));
  report.profile = profile;
  const chromeLog = fs.openSync(path.join(out, 'chrome.log'), 'w');
  chrome = spawn(chromePath, ['--headless=new', '--remote-debugging-port=0',
    '--disable-crashpad-for-testing',
    '--no-sandbox', '--no-zygote', '--single-process', '--disable-gpu',
    `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
    '--disable-background-networking', '--disable-component-update', '--disable-default-apps',
    '--disable-extensions', '--disable-sync', '--metrics-recording-only', '--mute-audio',
    '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
    '--force-color-profile=srgb', '--window-size=1440,1000', 'about:blank'],
  { windowsHide: true, stdio: ['ignore', chromeLog, chromeLog] });
  fs.closeSync(chromeLog);
  let spawnError;
  chrome.on('error', error => { spawnError = error; });
  const portFile = path.join(profile, 'DevToolsActivePort');
  await until('Chrome debug port', () => {
    if (spawnError) throw spawnError;
    return fs.existsSync(portFile);
  }, 20000);
  const port = Number(fs.readFileSync(portFile, 'utf8').split(/\r?\n/)[0]);
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = targets.find(target => target.type === 'page');
  requireCondition(page, 'Chrome did not create an isolated page');
  cdp = new CDP(page.webSocketDebuggerUrl);
  const allowedOrigin = new URL(base).origin;
  cdp.on('Fetch.requestPaused', event => {
    const permitted = event.request.url.startsWith(allowedOrigin + '/') || /^(data|blob):/.test(event.request.url);
    if (!permitted) report.externalRequests.push(event.request.url);
    cdp.send(permitted ? 'Fetch.continueRequest' : 'Fetch.failRequest', permitted ?
      { requestId: event.requestId } : { requestId: event.requestId, errorReason: 'BlockedByClient' })
      .catch(error => report.browserErrors.push({ kind: 'interception', message: error.message }));
  });
  cdp.on('Runtime.exceptionThrown', event => recordError(report.browserErrors, { kind: 'exception',
    message: event.exceptionDetails.exception?.description || event.exceptionDetails.text }));
  cdp.on('Runtime.consoleAPICalled', event => {
    const item = { kind: 'console', message: event.args.map(arg => arg.value ?? arg.description).join(' ') };
    if (event.type === 'error') recordError(report.browserErrors, item);
    if (event.type === 'warning' || event.type === 'warn') report.consoleWarnings.push(item);
  });
  cdp.on('Log.entryAdded', event => {
    if (event.entry.level === 'error') recordError(report.browserErrors, { kind: event.entry.source, message: event.entry.text });
    if (event.entry.level === 'warning') report.consoleWarnings.push({ kind: event.entry.source, message: event.entry.text });
  });
  cdp.on('Network.requestWillBeSent', event => {
    if (event.request.url.startsWith(allowedOrigin + '/')) activeRequests.add(event.requestId);
    lastNetworkActivity = Date.now();
  });
  for (const method of ['Network.loadingFinished', 'Network.loadingFailed']) cdp.on(method, event => {
    activeRequests.delete(event.requestId);
    lastNetworkActivity = Date.now();
    if (method.endsWith('Failed') && !event.canceled && event.errorText !== 'net::ERR_ABORTED')
      recordError(report.networkErrors, { requestId: event.requestId, message: event.errorText });
  });
  cdp.on('Network.responseReceived', event => {
    if (event.response.status >= 400) report.networkErrors.push({ url: event.response.url, status: event.response.status });
    if (event.response.status === 206) report.rangeResponses.push({ url: event.response.url,
      range: Object.entries(event.response.headers).find(([key]) => key.toLowerCase() === 'content-range')?.[1] });
  });
  for (const method of ['Page.enable', 'Runtime.enable', 'Network.enable', 'Log.enable']) await cdp.send(method);
  await cdp.send('Fetch.enable', { patterns: [{ urlPattern: '*', requestStage: 'Request' }] });
  report.browser = await cdp.send('Browser.getVersion');
  await viewport(1440, 1000);
  await cdp.send('Page.navigate', { url: base });
  const scenarios = await check('four scenarios and API connected', async () => {
    await until('four loaded scenarios', () => cdp.evaluate("document.querySelectorAll('.scen').length === 4 && !!document.querySelector('.api-connected')"));
    const labels = await cdp.evaluate("[...document.querySelectorAll('.scen strong')].map(el => el.textContent)");
    requireCondition(labels.length === 4, 'Expected four scenarios');
    return labels;
  });
  requireCondition(scenarios, 'App did not load; stopping subsequent checks');

  for (const scenario of scenarios) {
    await selectScenario(scenario);
    for (const layer of ['Depth', 'Velocity', 'Arrival', 'Extent']) await check(`Explore ${scenario} ${layer}`, async () => {
      await click('[aria-label="Map layer"] button', layer);
      const canvases = await mapsReady(1);
      const text = await cdp.evaluate("document.querySelector('.inspector').textContent");
      requireCondition(text.includes(scenario), 'Scenario inspector differs from selection');
      await screenshot(`explore-${scenario}-${layer}`);
      return { canvases, rangeResponses: report.rangeResponses.length };
    });
  }
  await click('nav[aria-label="Sections"] button', 'Compare');
  await check('Compare four rows and scenario selections', async () => {
    await until('Compare table', () => cdp.evaluate("document.querySelectorAll('tbody tr').length === 4 && document.querySelectorAll('.pick select').length === 2"));
    const options = await cdp.evaluate("[...document.querySelectorAll('.pick select')].map(select => select.options.length)");
    requireCondition(options.every(count => count === 4), 'Compare selector options missing');
    await cdp.evaluate("(() => { const right = document.querySelectorAll('.pick select')[1]; right.selectedIndex = 3; right.dispatchEvent(new Event('change', {bubbles:true})); })()");
    await pause(100);
    return options;
  });
  for (const layer of ['Depth', 'Velocity', 'Arrival', 'Extent']) await check(`Compare ${layer}`, async () => {
    await click('[aria-label="Map layer"] button', layer);
    const canvases = await mapsReady(2);
    await screenshot(`compare-${layer}`, true);
    return canvases;
  });
  await click('nav[aria-label="Sections"] button', 'Evidence');
  for (const scenario of scenarios) await check(`Evidence ${scenario}`, async () => {
    await selectScenario(scenario);
    await until('evidence assets', () => cdp.evaluate("document.querySelectorAll('.downloads a').length >= 6"));
    const info = await cdp.evaluate(`(() => ({ text: document.querySelector('.evidence').textContent,
      links: [...document.querySelectorAll('.downloads a')].map(el => ({href: el.href, download: el.hasAttribute('download')})) }))()`);
    requireCondition(/Calibration: uncalibrated/.test(info.text) && /Scientifically validated: no/.test(info.text), 'Prototype status missing');
    requireCondition(info.links.every(link => link.href.startsWith(allowedOrigin + '/api/') && link.download), 'Download escaped local API or lacked download attribute');
    await screenshot(`evidence-${scenario}-metadata`, true);
    await click('summary', 'Technical details');
    for (const title of ['Stored assumptions (JSON)', 'Stored quality report (JSON)']) {
      await click('summary', title);
      await until('stored JSON preview', () => cdp.evaluate(`(() => {
        const detail = [...document.querySelectorAll('details')].find(el => el.querySelector('summary')?.textContent === ${JSON.stringify(title)});
        const pre = detail?.querySelector('pre');
        if (!pre) return false;
        JSON.parse(pre.textContent);
        return true;
      })()`));
    }
    await settled();
    await cdp.evaluate("document.querySelector('.tech').scrollIntoView({block:'start'})");
    await screenshot(`evidence-${scenario}-json`, true);
    return { downloads: info.links.length, storedJsonPreviews: 2 };
  });

  await viewport(375, 812);
  for (const section of ['Explore', 'Compare', 'Evidence']) await check(`Mobile 375px ${section}`, async () => {
    await click('nav[aria-label="Sections"] button', section);
    if (section !== 'Evidence') await mapsReady(section === 'Compare' ? 2 : 1);
    else await until('mobile evidence', () => cdp.evaluate("document.querySelectorAll('.downloads a').length >= 6"));
    const size = await cdp.evaluate(`({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
      nav: [...document.querySelectorAll('nav button')].map(el => ({ text: el.textContent.trim(), width: el.getBoundingClientRect().width })) })`);
    requireCondition(size.width === 375 && size.scrollWidth <= 376, `Page overflow: ${JSON.stringify(size)}`);
    requireCondition(size.nav.every(button => button.width > 0), 'Mobile navigation hidden');
    await screenshot(`mobile-${section}`, true);
    return size;
  });
  await viewport(1440, 1000);
  await check('Browser offline status and actionable banner', async () => {
    // Emulation applies only to this isolated Chrome target; all services stay running.
    offlineTestStarted = true;
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    await cdp.send('Network.emulateNetworkConditions', { offline: true, latency: 0,
      downloadThroughput: 0, uploadThroughput: 0 });
    try {
      await click('nav[aria-label="Sections"] button', 'Explore');
      await until('offline API status and banner', () => cdp.evaluate(`!!document.querySelector('.api-unreachable') &&
        [...document.querySelectorAll('.banner')].some(el => /The API did not answer/.test(el.textContent))`), 30000);
      const feedback = await cdp.evaluate(`({ status: document.querySelector('.api-unreachable').textContent,
        banner: document.querySelector('.banner').textContent,
        retry: !!document.querySelector('.banner button') })`);
      requireCondition(feedback.retry, 'Offline message has no retry action');
      await screenshot('offline-feedback');
      return feedback;
    } finally {
      await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 0,
        downloadThroughput: -1, uploadThroughput: -1 });
    }
  });
  await check('Browser online recovery and map reload', async () => {
    if (await cdp.evaluate("!!document.querySelector('.banner button')")) await click('.banner button', 'Try again');
    await until('API reconnects', () => cdp.evaluate("!!document.querySelector('.api-connected')"), 30000);
    const canvases = await mapsReady(1);
    requireCondition(await cdp.evaluate("document.querySelectorAll('.banner').length === 0"), 'Error banner remained after recovery');
    await screenshot('online-recovered');
    return { canvases, expectedOfflineErrors: report.expectedOfflineErrors.length };
  });
  await check('COG partial content and no browser/network errors', async () => {
    requireCondition(report.rangeResponses.length > 0 && report.rangeResponses.every(item => /^bytes /.test(item.range)), 'No valid COG partial-content responses');
    requireCondition(report.externalRequests.length === 0, 'App attempted external network requests');
    requireCondition(report.browserErrors.length === 0, JSON.stringify(report.browserErrors));
    requireCondition(report.networkErrors.length === 0, JSON.stringify(report.networkErrors));
    return { partialContentResponses: report.rangeResponses.length, consoleWarnings: report.consoleWarnings.length };
  });
}

main().catch(error => {
  report.fatal = error.stack || error.message;
  console.error(error.message);
}).finally(async () => {
  report.finished = new Date().toISOString();
  report.passed = !report.fatal && report.checks.length > 0 && report.checks.every(check => check.passed);
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(out, 'browser-report.json'), JSON.stringify(report, null, 2));
  if (cdp) {
    await cdp.send('Browser.close').catch(() => {});
    cdp.close();
  }
  if (chrome && chrome.exitCode === null) chrome.kill();
  // Keep the isolated profile for diagnosis. It is outside both transfer roots.
  console.log(`Browser evidence: ${out}`);
  console.log(`Result: ${report.passed ? 'PASS' : 'FAIL'} (${report.checks.filter(check => check.passed).length}/${report.checks.length})`);
  process.exitCode = report.passed ? 0 : 1;
});
