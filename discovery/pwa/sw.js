self.addEventListener("push", event => {
  let data = {};
  try { data = event.data.json(); } catch (_) {}
  event.waitUntil(self.registration.showNotification(data.title || "HaoToday", {
    body: data.body || "有一条新的权益提醒。", icon:"/icon-192.png", tag:data.tag,
    data:{path:data.path === "/devices/" ? "/devices/" : "/inbox/"}
  }));
});
self.addEventListener("notificationclick", event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.path));
});
