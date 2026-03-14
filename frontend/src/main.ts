import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";
import { pinia } from "./stores/index";
import "./style.css";

const app = createApp(App);

app.use(pinia);
app.use(router);

const authStore = useAuthStore(pinia);
authStore.bindAuthListener();
authStore.refreshSession().catch(() => {
  // non-fatal: auth state will be updated on first navigation
});

app.mount("#app");
