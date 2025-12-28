export default [
    {
        path: '/home',
        name: 'home',
        component: () => import('../views/home/home.vue'),
        redirect: '/home/eeg',  // 默认显示脑电采集页
        children: [
            {
                path: 'info',
                name: 'info',
                component: () => import('../components/home/info-form.vue')
            },
            {
                path: 'video',
                name: 'video',
                component: () => import('../views/home/video.vue')
            },
            {
                path: 'game',
                name: 'game',
                component: () => import('../views/home/ARandVR.vue')
            },
            {
                path: 'music',
                name: 'music',
                component: () => import('../views/home/music.vue')
            },
            {
                path: 'eeg',
                name: 'eeg',
                component: () => import('../views/home/eeg.vue')
            }
        ]
    },

    {
        path: '/',
        redirect: '/login'
    },
    {
        path: '/login',
        name: 'login',
        meta: {
            title: 'Login - 登录',
            hideInMenu: true
        },
        component: () => import('../views/login/login.vue')
    },
    {
        path: '/register',
        name: 'register',
        redirect: '/login'
    },
]