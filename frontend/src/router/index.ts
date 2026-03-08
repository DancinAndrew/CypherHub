import { createRouter, createWebHistory } from "vue-router";

import EventDetailView from "../views/EventDetailView.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import MyTicketsView from "../views/MyTicketsView.vue";
import OrganizerCheckinView from "../views/OrganizerCheckinView.vue";
import OrganizerManageView from "../views/OrganizerManageView.vue";
import { useAuthStore } from "../stores/auth";
import { pinia } from "../stores/index";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/events/:eventId",
      name: "event-detail",
      component: EventDetailView,
    },
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/tickets",
      name: "my-tickets",
      component: MyTicketsView,
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer",
      name: "organizer-manage",
      component: OrganizerManageView,
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/checkin/:eventId",
      name: "organizer-checkin",
      component: OrganizerCheckinView,
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/checkin",
      name: "organizer-checkin-manual",
      component: OrganizerCheckinView,
      meta: { requiresAuth: true },
    },
  ],
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia);

  if (!authStore.initialized) {
    try {
      await authStore.refreshSession();
    } catch (error) {
      console.error("Session refresh failed", error);
    }
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: "login",
      query: { redirect: to.fullPath },
    };
  }

  if (to.name === "login" && authStore.isAuthenticated) {
    return { name: "home" };
  }

  return true;
});

export default router;
