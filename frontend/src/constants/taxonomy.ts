export const DANCE_STYLES = [
  { key: "hiphop", label: "HipHop" },
  { key: "popping", label: "Popping" },
  { key: "locking", label: "Locking" },
  { key: "house", label: "House" },
  { key: "waacking", label: "Waacking" },
  { key: "breaking", label: "Breaking" },
  { key: "krump", label: "Krump" },
  { key: "voguing", label: "Voguing" },
  { key: "freestyle", label: "Freestyle" },
  { key: "choreo", label: "Choreo" },
  { key: "allstyle", label: "AllStyle" },
] as const;

export const EVENT_TYPES = [
  { key: "cypher", label: "Cypher" },
  { key: "battle", label: "Battle" },
  { key: "group_battle", label: "Group Battle" },
  { key: "workshop", label: "Workshop" },
  { key: "jam", label: "Jam" },
  { key: "showcase", label: "Showcase" },
  { key: "audition", label: "Audition" },
  { key: "party", label: "Party" },
] as const;

export type DanceStyleKey = (typeof DANCE_STYLES)[number]["key"];
export type EventTypeKey = (typeof EVENT_TYPES)[number]["key"];

export function styleLabelFromKey(key: string): string {
  return DANCE_STYLES.find((item) => item.key === key)?.label ?? key;
}

export function eventTypeLabelFromKey(key: string): string {
  return EVENT_TYPES.find((item) => item.key === key)?.label ?? key;
}
