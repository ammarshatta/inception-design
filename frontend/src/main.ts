import { createApp } from 'vue'
import router from './router'
import App from './App.vue'
import './index.css'
import { __ } from './translate'

import { Button, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'

const app = createApp(App)
setConfig('resourceFetcher', frappeRequest)

app.config.globalProperties.__ = __
app.use(router)
app.use(resourcesPlugin)

app.component('Button', Button)
app.mount('#app')

// PWA: the service worker caches static assets only (never /api).
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  navigator.serviceWorker
    .register('/api/method/construction_core.api.public.service_worker', { scope: '/portal/' })
    .catch(() => {})
}
