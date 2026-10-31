// Service worker: deixa o app instalável, abre rápido e exibe notificações.
const CACHE = "compras-v2";
const API_CACHE = "compras-api"; // última versão das listas e itens, para abrir sem internet
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
      Promise.all(
        keys.filter((key) => key !== CACHE && key !== API_CACHE).map((key) => caches.delete(key)),
      ),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) {
    if (url.pathname !== "/api/events") event.respondWith(apiNetworkFirst(event.request));
    return;
  }
  // Arquivos do app: usa o cache e atualiza em segundo plano.
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

// API: sempre busca no servidor; sem conexão, devolve a última resposta salva
// (marcada com X-From-Cache para o app avisar que pode estar desatualizada).
async function apiNetworkFirst(request) {
  const cache = await caches.open(API_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    else if (response.status === 401 || response.status === 404) await cache.delete(request);
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (!cached) throw error;
    const headers = new Headers(cached.headers);
    headers.set("X-From-Cache", "1");
    return new Response(cached.body, { status: cached.status, headers });
  }
}

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
