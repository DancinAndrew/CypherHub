import { createRouter, createWebHistory } from "vue-router";

import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
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
      component: () => import("../views/EventDetailView.vue"),
    },
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/reset-password",
      name: "reset-password",
      component: () => import("../views/ResetPasswordView.vue"),
    },
    {
      path: "/orders/:orderId",
      name: "order-detail",
      component: () => import("../views/OrderDetailView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/tickets",
      name: "my-tickets",
      component: () => import("../views/MyTicketsView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/profile",
      name: "profile",
      component: () => import("../views/ProfileView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/admin",
      name: "admin",
      component: () => import("../views/AdminView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer",
      name: "organizer-home",
      component: () => import("../views/organizer/OrganizerHomeView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/apply",
      name: "organizer-apply",
      component: () => import("../views/organizer/OrganizerApplyView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/events",
      redirect: { name: "organizer-event-create" },
    },
    {
      path: "/organizer/events/create",
      name: "organizer-event-create",
      component: () => import("../views/organizer/OrganizerEventView.vue"),
      meta: { requiresAuth: true, eventMode: "create" },
    },
    {
      path: "/organizer/events/edit",
      name: "organizer-event-edit",
      component: () => import("../views/organizer/OrganizerEventView.vue"),
      meta: { requiresAuth: true, eventMode: "edit" },
    },
    {
      path: "/organizer/events/edit/:eventId",
      name: "organizer-event-edit-by-id",
      component: () => import("../views/organizer/OrganizerEventView.vue"),
      meta: { requiresAuth: true, eventMode: "edit" },
    },
    {
      path: "/organizer/forms",
      name: "organizer-forms",
      component: () => import("../views/organizer/OrganizerFormBuilderView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/forms/:eventId",
      name: "organizer-forms-with-event",
      component: () => import("../views/organizer/OrganizerFormBuilderView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/checkin/:eventId",
      name: "organizer-checkin",
      component: () => import("../views/organizer/OrganizerCheckinView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/checkin",
      name: "organizer-checkin-manual",
      component: () => import("../views/organizer/OrganizerCheckinView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/progress/:eventId",
      name: "organizer-progress",
      component: () => import("../views/organizer/OrganizerProgressView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/manage",
      name: "organizer-manage",
      component: () => import("../views/organizer/OrganizerManageView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/members",
      name: "organizer-members",
      component: () => import("../views/organizer/OrganizerMembersView.vue"),
      meta: { requiresAuth: true },
    },
    ...(import.meta.env.DEV
      ? [
          {
            path: "/__test-error",
            name: "error-boundary-test",
            component: () => import("../views/ErrorBoundaryTestView.vue"),
          },
        ]
      : []),
  ],
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia);

  if (!authStore.initialized) {
    try {
      await authStore.refreshSession();
    } catch {
      // non-fatal: proceed with current session state
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
