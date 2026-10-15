// Per-browser preferences; storage may be unavailable (private mode, blocked site data).
export const storage = {
  get(key: string, fallback: string) {
    try {
      return localStorage.getItem(key) ?? fallback
    } catch {
      return fallback
    }
  },
  set(key: string, value: string) {
    try {
      localStorage.setItem(key, value)
    } catch {
      /* not persisted */
    }
  },
}
