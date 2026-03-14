import type { AuthChangeEvent, Session, User } from "@supabase/supabase-js";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { supabase } from "../api/supabase";

type SignUpResult = {
  email: string;
  requiresEmailConfirmation: boolean;
};

export const useAuthStore = defineStore("auth", () => {
  const session = ref<Session | null>(null);
  const user = ref<User | null>(null);
  const initialized = ref(false);
  let subscriptionBound = false;

  const accessToken = computed(() => session.value?.access_token ?? null);
  const isAuthenticated = computed(() => Boolean(accessToken.value));

  async function refreshSession(): Promise<void> {
    const { data, error } = await supabase.auth.getSession();
    if (error) {
      throw error;
    }

    session.value = data.session;
    user.value = data.session?.user ?? null;
    initialized.value = true;
  }

  function bindAuthListener(): void {
    if (subscriptionBound) {
      return;
    }

    const { data } = supabase.auth.onAuthStateChange(
      (_event: AuthChangeEvent, nextSession: Session | null) => {
        session.value = nextSession;
        user.value = nextSession?.user ?? null;
        initialized.value = true;
      },
    );

    subscriptionBound = true;

    window.addEventListener("beforeunload", () => {
      data.subscription.unsubscribe();
      subscriptionBound = false;
    });
  }

  async function signUp(email: string, password: string): Promise<SignUpResult> {
    const normalizedEmail = email.trim().toLowerCase();
    const { data, error } = await supabase.auth.signUp({
      email: normalizedEmail,
      password,
    });
    if (error) {
      throw error;
    }

    await refreshSession();
    return {
      email: normalizedEmail,
      requiresEmailConfirmation: !data.session,
    };
  }

  async function signIn(email: string, password: string): Promise<void> {
    const normalizedEmail = email.trim().toLowerCase();
    const { error } = await supabase.auth.signInWithPassword({
      email: normalizedEmail,
      password,
    });
    if (error) {
      throw error;
    }

    await refreshSession();
  }

  async function signOut(): Promise<void> {
    const { error } = await supabase.auth.signOut();
    if (error) {
      throw error;
    }

    session.value = null;
    user.value = null;
  }

  /** 僅清除本地 session（如 401 時），不呼叫 Supabase signOut。 */
  function clearSession(): void {
    session.value = null;
    user.value = null;
  }

  return {
    session,
    user,
    initialized,
    accessToken,
    isAuthenticated,
    refreshSession,
    bindAuthListener,
    signUp,
    signIn,
    signOut,
    clearSession,
  };
});
