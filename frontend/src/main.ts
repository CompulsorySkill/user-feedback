import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { loadSiteName } from './config/site'
import './style.css'
import './styles/write-path.css'
import './styles/typography.css'
import './styles/tags.css'
import './styles/audit.css'
import './styles/attachments.css'

async function bootstrap(): Promise<void> {
  await loadSiteName()
  createApp(App).use(createPinia()).use(router).mount('#app')
}

void bootstrap()
