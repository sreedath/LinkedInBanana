"use client";

import { useEffect, useState } from "react";
import {
  getLinkedInStatus,
  postToLinkedIn,
  scheduleLinkedInPost,
} from "@/lib/api";

interface Props {
  caption: string;
  imagePath?: string;
}

export function LinkedInPostActions({ caption, imagePath }: Props) {
  const [authenticated, setAuthenticated] = useState(false);
  const [linkedInName, setLinkedInName] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("");

  useEffect(() => {
    checkStatus();
  }, []);

  async function checkStatus() {
    try {
      const status = await getLinkedInStatus();
      setAuthenticated(status.authenticated);
      if (status.name) setLinkedInName(status.name);
    } catch {
      // Not authenticated
    }
  }

  async function handlePostNow() {
    setLoading(true);
    setMessage("");
    try {
      const result = await postToLinkedIn(caption, imagePath);
      setMessage(`Posted successfully! (ID: ${result.post_id})`);
    } catch (err) {
      setMessage(`Post failed: ${err}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSchedule() {
    if (!scheduleDate || !scheduleTime) {
      setMessage("Please select both date and time");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const scheduledAt = new Date(`${scheduleDate}T${scheduleTime}`).toISOString();
      const result = await scheduleLinkedInPost(caption, imagePath, scheduledAt);
      setMessage(`Scheduled for ${new Date(result.scheduled_at).toLocaleString()}`);
    } catch (err) {
      setMessage(`Schedule failed: ${err}`);
    } finally {
      setLoading(false);
    }
  }

  if (!authenticated) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">Post to LinkedIn</h3>
        <p className="mt-2 text-sm text-gray-500">
          Connect your LinkedIn account on the{" "}
          <a href="/" className="text-blue-600 underline hover:text-blue-700">
            home page
          </a>{" "}
          first to post or schedule directly.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900">Post to LinkedIn</h3>

      {message && (
        <p className="mt-2 text-sm text-gray-600">{message}</p>
      )}

      <div className="mt-4 space-y-4">
        <p className="text-sm text-gray-500">
          Connected as <strong>{linkedInName}</strong>
        </p>

        {/* Post Now */}
        <button
          onClick={handlePostNow}
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Posting..." : "Post Now"}
        </button>

        {/* Schedule */}
        <div className="space-y-2 rounded-lg border border-gray-200 p-4">
          <p className="text-sm font-medium text-gray-700">Schedule for later</p>
          <div className="flex gap-2">
            <input
              type="date"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-banana-500 focus:outline-none"
            />
            <input
              type="time"
              value={scheduleTime}
              onChange={(e) => setScheduleTime(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-banana-500 focus:outline-none"
            />
          </div>
          <button
            onClick={handleSchedule}
            disabled={loading || !scheduleDate || !scheduleTime}
            className="w-full rounded-lg border border-blue-600 px-4 py-2 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50 disabled:opacity-50"
          >
            {loading ? "Scheduling..." : "Schedule Post"}
          </button>
        </div>
      </div>
    </div>
  );
}
