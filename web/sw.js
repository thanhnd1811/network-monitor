// Minimal service worker for offline shell.
// We deliberately do NOT cache data/status.json — always fresh from network.

const CACHE = "ftu-netmon-v1";
const SHELL = [
  "./",
  "./index.html",
  "./style.css",
  "./app.js",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Always fetch fresh for status/history JSON
  if (url.pathname.endsWith("status.json") || url.pathname.endsWith("history.json")) {
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
    return;
  }
  // App shell: cache-first
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
