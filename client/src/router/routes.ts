import type { RouteRecordRaw } from 'vue-router';

export enum Route {
  CONNECT = '/connect',
  LOBBY   = '/lobby',
  GAME    = '/game',
  END     = '/end',
  RANKING = '/ranking',
}

const routes: RouteRecordRaw[] = [
  { path: '/',           redirect: Route.CONNECT },
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: Route.CONNECT, component: () => import('pages/ConnectPage.vue') },
      {
        path: Route.LOBBY,
        component: () => import('pages/LobbyPage.vue'),
        meta: { requiresConnection: true },
      },
      {
        path: Route.GAME,
        component: () => import('pages/GamePage.vue'),
        meta: { requiresConnection: true },
      },
      {
        path: Route.END,
        component: () => import('pages/EndPage.vue'),
        meta: { requiresConnection: true },
      },
      {
        path: Route.RANKING,
        component: () => import('pages/RankingPage.vue'),
        meta: { requiresConnection: true },
      },
    ],
  },
  { path: '/:catchAll(.*)*', redirect: Route.CONNECT },
];

export default routes;
