const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    component: () => import('pages/LoginPage.vue'),
  },
  {
    path: '/lobby',
    component: () => import('pages/LobbyPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/game',
    component: () => import('pages/GamePage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/stats',
    component: () => import('pages/StatsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
]

export default routes
