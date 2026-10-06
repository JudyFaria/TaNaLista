// Service worker: deixa o app instalável, abre rápido e exibe notificações.
const CACHE = "compras-v1";
const SHELL = [
  "/",
  "/index.html",
  "/styles.css",
  "/icon.svg",
  "/manifest.webmanifest",
  "/js/app.js",
  "/js/api.js",
  "/js/dom.js",
  "/js/views.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
    ),
  );
  self.clients.claim();
});

// Arquivos do app: usa o cache e atualiza em segundo plano. A API nunca é cacheada.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) {
    return;
  }
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(event.request);
      const network = fetch(event.request)
        .then((response) => {
          if (response.ok) cache.put(event.request, response.clone());
          return response;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = event.notification.data?.url || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const client = clients.find((c) => new URL(c.url).origin === location.origin);
      if (client) {
        client.navigate(target);
        return client.focus();
      }
      return self.clients.openWindow(target);
    }),
  );
});
