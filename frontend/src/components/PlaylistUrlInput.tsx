"use client";

import { useState } from "react";

interface Props {
  value: string;
  onChange: (url: string) => void;
  disabled?: boolean;
}

export function PlaylistUrlInput({ value, onChange, disabled }: Props) {
  const [error, setError] = useState("");

  function validate(url: string) {
    if (!url) {
      setError("");
      return;
    }
    const hasPlaylistId =
      url.includes("list=") || /^PL[\w-]+$/.test(url);
    if (!hasPlaylistId) {
      setError("Please enter a valid YouTube playlist URL");
    } else {
      setError("");
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    e.preventDefault();
    const text = e.clipboardData.getData("text").trim();
    if (text) {
      onChange(text);
      validate(text);
    }
  }

  return (
    <div className="space-y-2">
      <label
        htmlFor="playlist-url"
        className="block text-sm font-medium text-gray-700"
      >
        YouTube Playlist URL
      </label>
      <input
        id="playlist-url"
        type="url"
        placeholder="https://www.youtube.com/playlist?list=PL..."
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          validate(e.target.value);
        }}
        onPaste={handlePaste}
        disabled={disabled}
        className="w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-900 placeholder-gray-400 focus:border-banana-500 focus:outline-none focus:ring-2 focus:ring-banana-200 disabled:bg-gray-100 disabled:text-gray-500"
      />
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}
