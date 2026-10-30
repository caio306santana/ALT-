// Caches only the app shell; /api always goes to the PC. Shows the PC's push notifications.
const SHELL = "alt-shell-v055";
const FILES = ["/", "/app.js", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];
self.addEventListener("install", (event) => event.waitUntil(caches.open(SHELL).then((c) => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener("activate", (event) => event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== SHELL).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== location.origin || url.pathname.startsWith("/api") || url.pathname === "/pair" || event.request.method !== "GET") return;
  event.respondWith(fetch(event.request).then((response) => {
    const copy = response.clone(); caches.open(SHELL).then((c) => c.put(event.request, copy)); return response;
  }).catch(() => caches.match(event.request)));
});
self.addEventListener("push", (event) => {
  let data = { title: "ALT", body: "" };
  try { data = event.data.json(); } catch (e) {}
  event.waitUntil(self.registration.showNotification(data.title || "ALT", { body: data.body || "", icon: "/icon-192.png", badge: "/icon-192.png" }));
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({ type: "window" }).then((list) => list.length ? list[0].focus() : self.clients.openWindow("/")));
});
