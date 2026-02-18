// In production (same origin), use relative URLs.
// In local dev (port 3000), point to the backend directly.
function getBackendUrl(): string {
  if (typeof window !== "undefined" && window.location.port === "3000") {
    return "http://localhost:8080";
  }
  return "";
}

export const BACKEND_URL = getBackendUrl();
export const API_BASE = `${BACKEND_URL}/api/v1`;

// ---------------------------------------------------------------------------
// Auth token management
// ---------------------------------------------------------------------------

const AUTH_TOKEN_KEY = "linkedinbanana_auth_token";

export function getAuthToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

export function setAuthToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export async function login(
  email: string,
  password: string
): Promise<{ token: string; email: string }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Invalid email or password");
  }
  const data = await res.json();
  setAuthToken(data.token);
  return data;
}

export async function checkAuth(): Promise<{ authenticated: boolean; email: string }> {
  const token = getAuthToken();
  if (!token) return { authenticated: false, email: "" };
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: authHeaders(),
    });
    if (!res.ok) {
      clearAuthToken();
      return { authenticated: false, email: "" };
    }
    return res.json();
  } catch {
    return { authenticated: false, email: "" };
  }
}

export interface PlaylistRequest {
  playlist_url: string;
  format: "landscape" | "square";
  generate_caption: boolean;
  custom_instructions: string;
  google_api_key: string;
  youtube_api_key: string;
}

const API_KEYS_STORAGE_KEY = "linkedinbanana_api_keys";

export function saveApiKeys(googleApiKey: string, youtubeApiKey: string): void {
  localStorage.setItem(
    API_KEYS_STORAGE_KEY,
    JSON.stringify({ google_api_key: googleApiKey, youtube_api_key: youtubeApiKey })
  );
}

export function loadApiKeys(): { google_api_key: string; youtube_api_key: string } {
  try {
    const stored = localStorage.getItem(API_KEYS_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        google_api_key: parsed.google_api_key || "",
        youtube_api_key: parsed.youtube_api_key || "",
      };
    }
  } catch {
    // ignore parse errors
  }
  return { google_api_key: "", youtube_api_key: "" };
}

export function clearApiKeys(): void {
  localStorage.removeItem(API_KEYS_STORAGE_KEY);
}

export async function fetchStoredApiKeys(): Promise<{ google_api_key: string; youtube_api_key: string }> {
  try {
    const res = await fetch(`${API_BASE}/api-keys`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch API keys");
    return res.json();
  } catch {
    return { google_api_key: "", youtube_api_key: "" };
  }
}

export async function saveApiKeysToBackend(
  googleApiKey: string,
  youtubeApiKey: string
): Promise<void> {
  await fetch(`${API_BASE}/api-keys`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ google_api_key: googleApiKey, youtube_api_key: youtubeApiKey }),
  });
}

export interface JobCreatedResponse {
  job_id: string;
  status: string;
}

export interface VideoInfo {
  title: string;
  duration_minutes: number;
  duration_seconds: number;
}

export interface PlaylistInfo {
  title: string;
  channel: string;
  video_count: number;
  total_duration_minutes: number;
  total_views: number;
  videos: VideoInfo[];
}

export interface IterationImage {
  iteration: number;
  image_url: string;
}

export interface JobResult {
  image_url: string;
  iteration_images: IterationImage[];
  caption: string;
  description: string;
  hashtags: string[];
  playlist_title: string;
  video_count: number;
}

export interface JobStatus {
  job_id: string;
  status: string;
  phase: string;
  message: string;
  progress: number;
  playlist_info: PlaylistInfo | null;
  result: JobResult | null;
  error: string | null;
}

export async function submitPlaylist(
  request: PlaylistRequest
): Promise<JobCreatedResponse> {
  const res = await fetch(`${API_BASE}/playlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Failed to submit playlist");
  }
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error("Failed to get job status");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// LinkedIn API
// ---------------------------------------------------------------------------

export async function getLinkedInAuthUrl(
  redirectUri: string
): Promise<{ url: string }> {
  const params = new URLSearchParams({ redirect_uri: redirectUri });
  const res = await fetch(`${API_BASE}/linkedin/auth-url?${params}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to get auth URL");
  return res.json();
}

export async function getLinkedInStatus(): Promise<{
  authenticated: boolean;
  name?: string;
  linkedin_id?: string;
  org_id?: string;
  org_name?: string;
}> {
  const res = await fetch(`${API_BASE}/linkedin/status`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to check LinkedIn status");
  return res.json();
}

export async function postToLinkedIn(
  caption: string,
  imagePath?: string
): Promise<{ post_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/linkedin/post`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ caption, image_path: imagePath }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Post failed" }));
    throw new Error(err.detail || "Failed to post to LinkedIn");
  }
  return res.json();
}

export async function scheduleLinkedInPost(
  caption: string,
  imagePath?: string,
  scheduledAt?: string
): Promise<{ id: string; scheduled_at: string; status: string }> {
  const res = await fetch(`${API_BASE}/linkedin/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ caption, image_path: imagePath, scheduled_at: scheduledAt }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Schedule failed" }));
    throw new Error(err.detail || "Failed to schedule post");
  }
  return res.json();
}

export function createJobStream(
  jobId: string,
  onStatus: (data: {
    status: string;
    phase: string;
    message: string;
    progress: number;
  }) => void,
  onComplete: (result: JobResult) => void,
  onError: (error: string) => void
): EventSource {
  const token = getAuthToken();
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
  const es = new EventSource(`${API_BASE}/jobs/${jobId}/stream${tokenParam}`);

  es.addEventListener("status", (e) => {
    const data = JSON.parse(e.data);
    onStatus(data);
  });

  es.addEventListener("complete", (e) => {
    const data = JSON.parse(e.data);
    onComplete(data);
    es.close();
  });

  es.addEventListener("error", (e) => {
    if (e instanceof MessageEvent && e.data) {
      const data = JSON.parse(e.data);
      onError(data.error || "Unknown error");
    } else {
      onError("Connection lost");
    }
    es.close();
  });

  return es;
}
