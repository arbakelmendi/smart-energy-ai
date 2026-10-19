/** Local prototype state only; this is not authentication or authorization. */
export function parseDemoSession(raw: string): {
  name: string; email: string; role: "Building Admin" | "Analyst" | "Viewer" | "Platform Admin"; onboarded: boolean;
} | null {
  try {
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object") return null;
    const item = value as Record<string, unknown>;
    const roles = ["Building Admin", "Analyst", "Viewer", "Platform Admin"] as const;
    if (typeof item["name"] !== "string" || typeof item["email"] !== "string" || typeof item["onboarded"] !== "boolean"
      || !roles.some(role => role === item["role"])) return null;
    return { name: item["name"], email: item["email"], role: item["role"] as typeof roles[number], onboarded: item["onboarded"] };
  } catch { return null; }
}
