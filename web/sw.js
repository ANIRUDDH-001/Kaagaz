// Service worker: shows reminder pushes. Same tag = same reminder, so a re-sent push replaces, never doubles.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { d = { body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(d.title || "काग़ज़ · Kaagaz", {
    body: d.body || "",
    tag: d.tag,
    icon: "icon.svg",
    badge: "icon.svg",
    data: { role: d.role || "parent" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = `./?role=${e.notification.data?.role || "parent"}`;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
    for (const w of wins) { if ("focus" in w) { w.navigate(url); return w.focus(); } }
    return self.clients.openWindow(url);
  }));
});
