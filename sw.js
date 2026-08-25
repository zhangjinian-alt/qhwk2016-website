/* 青花微课 PWA - Service Worker
 * 策略：
 *   - 导航请求 (HTML): network-first，失败回缓存（可离线打开）
 *   - 静态资源 (图片/CSS/JS/字体): stale-while-revalidate
 *   - /api/* 与非 GET 请求: 全部 network-only（绝不能缓存鉴权/动态数据）
 *   - 绝不缓存 index.html 自身（年哥哥用 ?v= 强刷调试，避免 SW 抢先返回老 HTML）
 */
const CACHE = 'qhwk-shell-v1';
const SHELL = [
  '/site-2026.webmanifest',
  '/android-chrome-192x192-2026.png',
  '/android-chrome-512x512-2026.png',
  '/apple-touch-icon-2026.png',
  '/favicon-2026.ico'
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => {})));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;                 // POST/PUT 等一律不拦截
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   // 跨域（CDN 脚本等）放行
  if (url.pathname.startsWith('/api/')) return;     // 鉴权/动态数据，绝不缓存

  // HTML 导航：network-first，失败回缓存
  if (req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html')) {
    if (url.pathname === '/' || url.pathname === '/index.html') {
      // 主页交给浏览器默认缓存策略（年哥哥用 ?v= 强刷），SW 不拦
      return;
    }
    e.respondWith(
      fetch(req).then((r) => {
        const copy = r.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return r;
      }).catch(() => caches.match(req).then((r) => r || caches.match('/')))
    );
    return;
  }

  // 静态资源：stale-while-revalidate
  e.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(req);
      const fetchPromise = fetch(req).then((r) => {
        if (r.ok) cache.put(req, r.clone());
        return r;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
