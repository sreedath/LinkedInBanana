"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ProgressTracker } from "@/components/ProgressTracker";
import { ImageResult } from "@/components/ImageResult";
import { CaptionDisplay } from "@/components/CaptionDisplay";
import { LinkedInPostActions } from "@/components/LinkedInPostActions";
import { API_BASE } from "@/lib/api";
import type { JobResult, PlaylistInfo } from "@/lib/api";

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function GenerateContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const jobId = searchParams.get("jobId") || "";

  const [phase, setPhase] = useState("scraping");
  const [message, setMessage] = useState("Starting...");
  const [progress, setProgress] = useState(0);
  const [playlistInfo, setPlaylistInfo] = useState<PlaylistInfo | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!jobId) return;

    let stopped = false;

    async function poll() {
      while (!stopped) {
        try {
          const status = await (await fetch(`${API_BASE}/jobs/${jobId}`)).json();

          if (stopped) break;

          setPhase(status.phase || "scraping");
          setMessage(status.message || "Processing...");
          setProgress(status.progress || 0);

          if (status.playlist_info) {
            setPlaylistInfo(status.playlist_info);
          }

          if (status.status === "complete" && status.result) {
            setResult(status.result);
            setPhase("complete");
            setProgress(1);
            setMessage("Complete!");
            return;
          }

          if (status.status === "error") {
            setError(status.error || "Unknown error");
            return;
          }
        } catch {
          // Network error — keep polling
        }

        await new Promise((r) => setTimeout(r, 2000));
      }
    }

    poll();

    return () => {
      stopped = true;
    };
  }, [jobId]);

  if (!jobId) {
    return (
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-gray-500">No job ID provided.</p>
        <button
          onClick={() => router.push("/")}
          className="mt-4 rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 hover:bg-gray-50"
        >
          Go Home
        </button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <h3 className="text-lg font-semibold text-red-700">
            Generation Failed
          </h3>
          <p className="mt-2 text-sm text-red-600">{error}</p>
        </div>
        <button
          onClick={() => router.push("/")}
          className="w-full rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 hover:bg-gray-50"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      {/* Progress section */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <ProgressTracker
          currentPhase={phase}
          message={message}
          progress={progress}
        />
      </div>

      {/* Playlist info section - shown once scraped */}
      {playlistInfo && !result && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Playlist Details
          </h3>
          <p className="mt-1 text-lg font-semibold text-gray-900">
            {playlistInfo.title}
          </p>
          <p className="text-sm text-gray-500">
            {playlistInfo.channel} &middot; {playlistInfo.video_count} videos &middot;{" "}
            {playlistInfo.total_duration_minutes} min total
          </p>

          <ul className="mt-4 max-h-60 space-y-1 overflow-y-auto">
            {playlistInfo.videos.map((v, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded px-2 py-1.5 text-sm odd:bg-gray-50"
              >
                <span className="mr-3 truncate text-gray-700">
                  <span className="mr-2 text-xs text-gray-400">{i + 1}.</span>
                  {v.title}
                </span>
                <span className="shrink-0 text-xs text-gray-400">
                  {formatDuration(v.duration_seconds)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Results section */}
      {result && (
        <div className="space-y-6">
          <ImageResult
            imageUrl={result.image_url}
            playlistTitle={result.playlist_title}
            iterationImages={result.iteration_images}
          />

          {result.caption && (
            <CaptionDisplay
              caption={result.caption}
              hashtags={result.hashtags}
            />
          )}

          {result.caption && (
            <LinkedInPostActions
              caption={result.caption}
              imagePath={result.image_url}
            />
          )}

          <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-600">
            <p>
              <strong>{result.playlist_title}</strong>,{" "}
              {result.video_count} videos
            </p>
          </div>

          <button
            onClick={() => router.push("/")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 hover:bg-gray-50"
          >
            Generate Another
          </button>
        </div>
      )}
    </div>
  );
}

export default function GeneratePage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-2xl text-center text-gray-500">Loading...</div>}>
      <GenerateContent />
    </Suspense>
  );
}
