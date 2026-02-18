"use client";

import { useState } from "react";

interface Props {
  caption: string;
  hashtags?: string[];
}

/** Recursively extract all text from a value that may be a nested object or array. */
function extractText(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value.map(extractText).filter(Boolean).join("\n\n");
  }
  if (typeof value === "object" && value !== null) {
    const obj = value as Record<string, unknown>;
    // Try common keys first
    for (const key of ["caption", "text", "content", "body"]) {
      if (key in obj) return extractText(obj[key]);
    }
    // Concatenate all values
    return Object.values(obj).map(extractText).filter(Boolean).join("\n\n");
  }
  return value ? String(value) : "";
}

/** If the string looks like raw JSON, try to extract the caption text from it. */
function cleanCaption(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return trimmed;

  try {
    const parsed = JSON.parse(trimmed);
    const extracted = extractText(parsed);
    if (extracted) return extracted;
  } catch {
    // Not valid JSON — return as-is
  }
  return trimmed;
}

export function CaptionDisplay({ caption }: Props) {
  const [editedCaption, setEditedCaption] = useState(cleanCaption(caption));
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(editedCaption);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">LinkedIn Caption</h3>
        <button
          onClick={handleCopy}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          {copied ? "Copied!" : "Copy to clipboard"}
        </button>
      </div>
      <textarea
        value={editedCaption}
        onChange={(e) => setEditedCaption(e.target.value)}
        rows={20}
        className="w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-900 focus:border-banana-500 focus:outline-none focus:ring-2 focus:ring-banana-200"
      />
    </div>
  );
}
