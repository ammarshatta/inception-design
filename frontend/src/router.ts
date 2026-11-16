import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('@/pages/Home.vue') },
  { path: '/projects/:name', name: 'Project', component: () => import('@/pages/ProjectPage.vue'), props: true },
  { path: '/projects/:name/update', name: 'NewUpdate', component: () => import('@/pages/NewUpdate.vue'), props: true },
  { path: '/projects/:name/daily', name: 'DailyLog', component: () => import('@/pages/DailyLogPage.vue'), props: true },
  { path: '/projects/:name/deliveries', name: 'Deliveries', component: () => import('@/pages/DeliveriesPage.vue'), props: true },
  { path: '/projects/:name/documents', name: 'Documents', component: () => import('@/pages/DocumentsPage.vue'), props: true },
  { path: '/c/:name/documents', name: 'ClientDocuments', component: () => import('@/pages/DocumentsPage.vue'), props: true },
  { path: '/markup', name: 'Markup', component: () => import('@/pages/MarkupPage.vue') },
  { path: '/takeoff/:name?', name: 'Takeoff', component: () => import('@/pages/TakeoffPage.vue'), props: true },
  { path: '/stages/:name', name: 'Stage', component: () => import('@/pages/StagePage.vue'), props: true },
  { path: '/foreman', name: 'Foreman', component: () => import('@/pages/ForemanPage.vue') },
  { path: '/sign/:name', name: 'Sign', component: () => import('@/pages/SignPage.vue'), props: true },
  { path: '/c/:project', name: 'ClientHome', component: () => import('@/pages/ClientHome.vue'), props: true },
  { path: '/c/:project/timeline', name: 'ClientTimeline', component: () => import('@/pages/ClientTimeline.vue'), props: true },
  { path: '/c/:project/gallery', name: 'ClientGallery', component: () => import('@/pages/ClientGallery.vue'), props: true },
  { path: '/c/:project/payments', name: 'ClientPayments', component: () => import('@/pages/ClientPayments.vue'), props: true },
  { path: '/c/:project/selections', name: 'ClientSelections', component: () => import('@/pages/ClientSelections.vue'), props: true },
  { path: '/c/:project/changes', name: 'ClientChanges', component: () => import('@/pages/ClientChanges.vue'), props: true },
  { path: '/c/:project/chat', name: 'Chat', component: () => import('@/pages/ChatPage.vue'), props: true },
]

const router = createRouter({
  history: createWebHistory('/portal'),
  routes,
})

export default router
