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
