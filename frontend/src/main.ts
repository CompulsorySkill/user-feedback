import { createPinia } from 'pinia';
import { createApp } from 'vue';

import App from './App.vue';
import { loadSiteName } from './config/site';
import router from './router';

import './style.css';
import './styles/write-path.css';
import './styles/typography.css';
import './styles/tags.css';
import './styles/audit.css';
import './styles/attachments.css';

async function bootstrap(): Promise<void> {
  await loadSiteName();
  createApp(App).use(createPinia()).use(router).mount('#app');
}

void bootstrap();
