"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { PlaylistUrlInput } from "@/components/PlaylistUrlInput";
import { FormatSelector } from "@/components/FormatSelector";
import { submitPlaylist, saveApiKeys, loadApiKeys } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [format, setFormat] = useState<"landscape" | "square">("landscape");
  const [generateCaption, setGenerateCaption] = useState(true);
  const [customInstructions, setCustomInstructions] = useState("");
  const [googleApiKey, setGoogleApiKey] = useState("");
  const [youtubeApiKey, setYoutubeApiKey] = useState("");
  const [showApiKeys, setShowApiKeys] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const keys = loadApiKeys();
    setGoogleApiKey(keys.google_api_key);
    setYoutubeApiKey(keys.youtube_api_key);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url || !googleApiKey || !youtubeApiKey) return;

    setLoading(true);
    setError("");
    saveApiKeys(googleApiKey, youtubeApiKey);

    try {
      const response = await submitPlaylist({
        playlist_url: url,
        format,
        generate_caption: generateCaption,
        custom_instructions: customInstructions,
        google_api_key: googleApiKey,
        youtube_api_key: youtubeApiKey,
      });
      router.push(`/generate?jobId=${response.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="space-y-2 text-center">
        <h2 className="text-3xl font-bold text-gray-900">
          Turn YouTube Playlists into LinkedIn Posts
        </h2>
        <p className="text-lg text-gray-600">
          Paste a playlist URL, get a professional image and caption ready to
          post on LinkedIn.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-6">
          <PlaylistUrlInput
            value={url}
            onChange={setUrl}
            disabled={loading}
          />

          <FormatSelector
            value={format}
            onChange={setFormat}
            disabled={loading}
          />

          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setShowApiKeys(!showApiKeys)}
              className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              <svg
                className={`h-4 w-4 transition-transform ${showApiKeys ? "rotate-90" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              API Keys
              {(!googleApiKey || !youtubeApiKey) && (
                <span className="text-xs text-red-500 font-normal">(required)</span>
              )}
            </button>
            {showApiKeys && (
              <div className="space-y-3 pl-6">
                <div>
                  <label htmlFor="google-api-key" className="block text-sm font-medium text-gray-700 mb-1">
                    Google Gemini API Key
                  </label>
                  <input
                    id="google-api-key"
                    type="password"
                    placeholder="AIza..."
                    value={googleApiKey}
                    onChange={(e) => setGoogleApiKey(e.target.value)}
                    disabled={loading}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 placeholder-gray-400 focus:border-banana-500 focus:outline-none focus:ring-2 focus:ring-banana-200 disabled:bg-gray-100 disabled:text-gray-500 text-sm font-mono"
                  />
                </div>
                <div>
                  <label htmlFor="youtube-api-key" className="block text-sm font-medium text-gray-700 mb-1">
                    YouTube Data API Key
                  </label>
                  <input
                    id="youtube-api-key"
                    type="password"
                    placeholder="AIza..."
                    value={youtubeApiKey}
                    onChange={(e) => setYoutubeApiKey(e.target.value)}
                    disabled={loading}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 placeholder-gray-400 focus:border-banana-500 focus:outline-none focus:ring-2 focus:ring-banana-200 disabled:bg-gray-100 disabled:text-gray-500 text-sm font-mono"
                  />
                </div>
                <p className="text-xs text-gray-400">
                  Keys are stored in your browser only and sent directly to Google APIs.
                </p>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label
              htmlFor="custom-instructions"
              className="block text-sm font-medium text-gray-700"
            >
              Custom Instructions{" "}
              <span className="font-normal text-gray-400">(optional)</span>
            </label>
            <textarea
              id="custom-instructions"
              placeholder="e.g. &quot;Use a dark theme with blue accents&quot;, &quot;Focus on the AI/ML topics&quot;, &quot;Make it look like a course curriculum&quot;..."
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              disabled={loading}
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-900 placeholder-gray-400 focus:border-banana-500 focus:outline-none focus:ring-2 focus:ring-banana-200 disabled:bg-gray-100 disabled:text-gray-500 text-sm"
            />
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={generateCaption}
              onChange={(e) => setGenerateCaption(e.target.checked)}
              disabled={loading}
              className="h-4 w-4 rounded border-gray-300 text-banana-500 focus:ring-banana-500"
            />
            <span className="text-sm text-gray-700">
              Generate LinkedIn article
            </span>
          </label>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!url || !googleApiKey || !youtubeApiKey || loading}
          className="w-full rounded-lg bg-banana-500 px-4 py-3 text-lg font-semibold text-white transition-colors hover:bg-banana-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Starting..." : "Generate LinkedIn Image"}
        </button>
      </form>

      <div className="text-center text-sm text-gray-500 space-y-1">
        <p>A simple frontend for PaperBanana, built by team Vizuara.</p>
        <p>Generates LinkedIn-ready images and articles from YouTube playlists using AI.</p>
      </div>
    </div>
  );
}
