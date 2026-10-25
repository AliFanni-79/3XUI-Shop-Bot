import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

import StoreView from '@/views/StoreView.vue'
import ServicesView from '@/views/ServicesView.vue'
import WalletView from '@/views/WalletView.vue'
import ReferralView from '@/views/ReferralView.vue'
import GuidesView from '@/views/GuidesView.vue'
import AdminDashboard from '@/views/admin/AdminDashboard.vue'

const routes = [
  { path: '/', name: 'store', component: StoreView },
  { path: '/services', name: 'services', component: ServicesView },
  { path: '/wallet', name: 'wallet', component: WalletView },
  { path: '/referral', name: 'referral', component: ReferralView },
  { path: '/guides', name: 'guides', component: GuidesView },
  {
    path: '/admin',
    name: 'admin',
    component: AdminDashboard,
    beforeEnter: (to, from, next) => {
      const auth = useAuthStore()
      if (auth.isAdmin) {
        next()
      } else {
        next('/')
      }
    }
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (typeof window !== 'undefined' && window.location.hash && window.location.hash.startsWith('#/')) {
    const targetPath = window.location.hash.slice(1)
    window.location.hash = ''
    return next(targetPath)
  }
  next()
})

export default router
