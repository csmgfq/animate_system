import { createRouter, createWebHashHistory } from 'vue-router';
import routes from './routes';

const router = createRouter({
    history: createWebHashHistory(),
    routes
})

// // 全局导航守卫
// router.beforeEach((to, from, next) => {
//     // 例如，如果需要验证用户登录状态
//     const isAuthenticated = false; // 假设未登录
//     if (to.meta.requiresAuth && !isAuthenticated) {
//         next({ name: 'login' }); // 重定向到登录页
//     } else {
//         next(); // 继续导航
//     }
// });

// // 处理未匹配的路由
// router.afterEach((to) => {
//     // 可以在这里做一些逻辑，比如记录页面访问
//     if (to.path === '/404') {
//         // 404页面的特殊处理
//     }
// });

export default router