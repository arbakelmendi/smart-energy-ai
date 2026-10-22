import { z } from "zod";
import { ApiError, apiRequest } from "./client.ts";

export const authUserSchema = z.object({
  id: z.number().int().positive(), email: z.string().email(), full_name: z.string(),
  role: z.enum(["USER", "ADMIN"]), is_active: z.literal(true),
}).strict();
export type AuthUser = z.infer<typeof authUserSchema>;
export interface SignupRequest { full_name: string; email: string; password: string }
export interface LoginRequest { email: string; password: string }

async function userRequest(path: string, options: RequestInit = {}): Promise<AuthUser> {
  const payload = await apiRequest<unknown>(path, { ...options, credentials: "include" });
  const parsed = authUserSchema.safeParse(payload);
  if (!parsed.success) throw new ApiError("Backend returned malformed account data.", 200);
  return parsed.data;
}
const options = (body?: LoginRequest | SignupRequest): RequestInit => ({
  method: "POST", credentials: "include",
  headers: { "Content-Type": "application/json", "X-SmartEnergy-CSRF": "1" },
  ...(body ? { body: JSON.stringify(body) } : {}),
});
export const signup = (body: SignupRequest) => userRequest("/auth/signup", options(body));
export const login = (body: LoginRequest) => userRequest("/auth/login", options(body));
export const logout = () => apiRequest<{ detail: string }>("/auth/logout", options());
export const getCurrentUser = (signal?: AbortSignal) => userRequest("/auth/me", signal ? { signal } : {});
