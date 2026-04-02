import { describe, it, expect } from "vitest";
import { useOrganizerStore } from "../../stores/organizer";

describe("useOrganizerStore", () => {
  it("初始狀態兩個值都是空字串", () => {
    const store = useOrganizerStore();
    expect(store.orgId).toBe("");
    expect(store.lastCreatedEventId).toBe("");
  });

  it("setOrgId('org-123') → orgId 更新", () => {
    const store = useOrganizerStore();
    store.setOrgId("org-123");
    expect(store.orgId).toBe("org-123");
  });

  it("setLastEventId('evt-456') → lastCreatedEventId 更新", () => {
    const store = useOrganizerStore();
    store.setLastEventId("evt-456");
    expect(store.lastCreatedEventId).toBe("evt-456");
  });
});
