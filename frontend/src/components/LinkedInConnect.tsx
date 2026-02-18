"use client";

import { useEffect, useState } from "react";
import { getLinkedInAuthUrl, getLinkedInStatus, BACKEND_URL } from "@/lib/api";

export function LinkedInConnect() {
  const [authenticated, setAuthenticated] = useState(false);
  const [linkedInName, setLinkedInName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    checkStatus();
  }, []);

  // Listen for OAuth popup messages
  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (event.data?.type === "linkedin-auth") {
        if (event.data.success) {
          setAuthenticated(true);
          setLinkedInName(event.data.name || "");
          setMessage("Connected to LinkedIn!");
        } else if (event.data.error) {
          setMessage(`Auth failed: ${event.data.error}`);
        }
      }
    }
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  async function checkStatus() {
    try {
      const status = await getLinkedInStatus();
      setAuthenticated(status.authenticated);
      if (status.name) setLinkedInName(status.name);
      if (status.org_name) setOrgName(status.org_name);
    } catch {
      // Not authenticated
    }
  }

  async function handleConnect() {
    setLoading(true);
    setMessage("");
    try {
      const origin = BACKEND_URL || window.location.origin;
      const redirectUri = `${origin}/api/v1/linkedin/callback`;
      const data = await getLinkedInAuthUrl(redirectUri);
      window.open(data.url, "linkedin-auth", "width=600,height=700");
    } catch (err) {
      setMessage(`Failed to start auth: ${err}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.32 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.79M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
        </svg>
        LinkedIn Connection
        {authenticated ? (
          <span className="text-xs text-green-600 font-normal">(connected)</span>
        ) : (
          <span className="text-xs text-gray-400 font-normal">(optional)</span>
        )}
      </div>

      {message && (
        <p className="text-sm text-gray-600 pl-6">{message}</p>
      )}

      {authenticated ? (
        <div className="text-sm text-gray-500 pl-6">
          <p>Connected as <strong>{linkedInName}</strong></p>
          {orgName && (
            <p className="mt-1">Posts will go to page: <strong>{orgName}</strong></p>
          )}
        </div>
      ) : (
        <div className="space-y-3 pl-6">
          <p className="text-sm text-gray-500">
            Connect your LinkedIn account to post or schedule directly from the results page.
          </p>
          <button
            type="button"
            onClick={handleConnect}
            disabled={loading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Connecting..." : "Connect LinkedIn"}
          </button>
        </div>
      )}
    </div>
  );
}
