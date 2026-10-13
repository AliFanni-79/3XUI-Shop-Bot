import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

// Expand the Mini App to full height and apply platform theme
const tg = window.Telegram?.WebApp
if (tg) {
  tg.expand()
  tg.ready()
}

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
