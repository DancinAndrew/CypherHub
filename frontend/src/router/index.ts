import { createRouter, createWebHistory } from "vue-router";

import AdminView from "../views/AdminView.vue";
import EventDetailView from "../views/EventDetailView.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import MyTicketsView from "../views/MyTicketsView.vue";
import ResetPasswordView from "../views/ResetPasswordView.vue";
import OrganizerApplyView from "../views/organizer/OrganizerApplyView.vue";
import OrganizerCheckinView from "../views/organizer/OrganizerCheckinView.vue";
import OrganizerEventView from "../views/organizer/OrganizerEventView.vue";
import OrganizerFormBuilderView from "../views/organizer/OrganizerFormBuilderView.vue";
import OrganizerHomeView from "../views/organizer/OrganizerHomeView.vue";
import OrganizerManageView from "../views/organizer/OrganizerManageView.vue";
import ProfileView from "../views/ProfileView.vue";
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
      path: "/reset-password",
      name: "reset-password",
      component: ResetPasswordView,
    },
    {
      path: "/tickets",
      name: "my-tickets",
      component: MyTicketsView,
      meta: { requiresAuth: true },
    },
    {
      path: "/profile",
      name: "profile",
      component: ProfileView,
      meta: { requiresAuth: true },
    },
    {
      path: "/admin",
      name: "admin",
      component: AdminView,
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer",
      name: "organizer-home",
      component: OrganizerHomeView,
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/apply",
      name: "organizer-apply",
      component: OrganizerApplyView,
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/events",
      redirect: { name: "organizer-event-create" },
    },
    {
      path: "/organizer/events/create",
      name: "organizer-event-create",
      component: OrganizerEventView,
      meta: { requiresAuth: true, eventMode: "create" },
    },
    {
      path: "/organizer/events/edit",
      name: "organizer-event-edit",
      component: OrganizerEventView,
      meta: { requiresAuth: true, eventMode: "edit" },
    },
    {
      path: "/organizer/events/edit/:eventId",
      name: "organizer-event-edit-by-id",
      component: OrganizerEventView,
      meta: { requiresAuth: true, eventMode: "edit" },
    },
    {
      path: "/organizer/forms",
      name: "organizer-forms",
      component: OrganizerFormBuilderView,
      meta: { requiresAuth: true },
    },
    {
      path: "/organizer/forms/:eventId",
      name: "organizer-forms-with-event",
      component: OrganizerFormBuilderView,
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
    {
      path: "/organizer/manage",
      name: "organizer-manage",
      component: OrganizerManageView,
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
