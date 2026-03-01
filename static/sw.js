// Service worker for ThinkPad Seeker PWA notifications
// Handles push events delivered by the server and shows them in the system tray

self.addEventListener('install', event => {
    // Activate the new service worker immediately without waiting
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    // Take control of all open pages immediately
    event.waitUntil(self.clients.claim());
});

// Listen for push events sent by the Flask backend
self.addEventListener('push', event => {
    // Parse the JSON payload sent by the server
    const data = event.data ? event.data.json() : {};

    const title = data.title || 'Scrape Complete';
    const options = {
        body: data.body || 'New listings are ready to review.',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-192.png',
        // tag prevents duplicate notifications if the push fires more than once
        tag: 'sar-scrape-result',
        // renotify: true causes the notification sound/vibration even if tag matches
        renotify: true,
        // data payload carries the URL to open when the notification is tapped
        data: { url: data.url || '/' }
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

// When the user taps the notification, open the app URL in the mobile browser
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const targetUrl = event.notification.data.url;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
            // If the app is already open, focus it instead of opening a new tab
            for (const client of clientList) {
                if (client.url === targetUrl && 'focus' in client) {
                    return client.focus();
                }
            }
            // Otherwise open a new browser tab
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
