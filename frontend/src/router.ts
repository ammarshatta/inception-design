import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('@/pages/Home.vue') },
  { path: '/projects/:name', name: 'Project', component: () => import('@/pages/ProjectPage.vue'), props: true },
  { path: '/projects/:name/update', name: 'NewUpdate', component: () => import('@/pages/NewUpdate.vue'), props: true },
  { path: '/stages/:name', name: 'Stage', component: () => import('@/pages/StagePage.vue'), props: true },
]

const router = createRouter({
  history: createWebHistory('/portal'),
  routes,
})

export default router
