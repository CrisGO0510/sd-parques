import { defineRouter } from '#q-app/wrappers';
import {
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router';
import routes, { Route } from './routes';
import { ConnectionStatus, useConnectionStore } from 'src/stores/connection';

/*
 * If not building with SSR mode, you can
 * directly export the Router instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Router instance.
 */

export default defineRouter(function (/* { store, ssrContext } */) {
  const createHistory = process.env['SERVER']
    ? createMemoryHistory
    : (process.env['VUE_ROUTER_MODE'] === 'history' ? createWebHistory : createWebHashHistory);

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,

    // Leave this as is and make changes in quasar.conf.js instead!
    // quasar.conf.js -> build -> vueRouterMode
    // quasar.conf.js -> build -> publicPath
    history: createHistory(process.env['VUE_ROUTER_BASE']),
  });

  Router.beforeEach((to) => {
    if (to.meta['requiresConnection']) {
      const conn = useConnectionStore();
      if (conn.status !== ConnectionStatus.CONNECTED) {
        return Route.CONNECT;
      }
    }
    return true;
  });

  return Router;
});
