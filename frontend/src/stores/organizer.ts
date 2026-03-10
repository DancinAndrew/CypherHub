import { defineStore } from "pinia";
import { ref } from "vue";

export const useOrganizerStore = defineStore("organizer", () => {
  const orgId = ref<string>("");
  const lastCreatedEventId = ref<string>("");

  function setOrgId(id: string) {
    orgId.value = id;
  }

  function setLastEventId(id: string) {
    lastCreatedEventId.value = id;
  }

  return { orgId, lastCreatedEventId, setOrgId, setLastEventId };
});
