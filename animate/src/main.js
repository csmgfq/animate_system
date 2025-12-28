import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css'; // 引入 Element Plus 的样式
import { createApp } from 'vue';
import axios from 'axios';

import './assets/fonts/alibaba-health-font.css';
import './styles/app.css';

import App from './App.vue';
import AudioPlayer from "./components/AudioPlayer.vue";
import router from './router';

const app = createApp(App)

// 自动为请求携带当前登录用户信息（后端用于权限与数据归属）
axios.interceptors.request.use((config) => {
    try {
        const raw = localStorage.getItem('currentUser');
        if (raw) {
            const user = JSON.parse(raw);
            if (user && user.id != null) {
                config.headers = config.headers || {};
                config.headers['X-User-Id'] = String(user.id);
            }
            if (user && user.account) {
                config.headers = config.headers || {};
                config.headers['X-User-Account'] = String(user.account);
            }
        }
    } catch (e) {
        // ignore
    }
    return config;
});

app.component("AudioPlayer", AudioPlayer);
app.use(ElementPlus)

app.use(router).mount('#app')
