"use client";

import { useState } from "react";
import { BACKEND_URL, getAuthToken } from "@/lib/api";
import type { IterationImage } from "@/lib/api";

interface Props {
  imageUrl: string;
  playlistTitle: string;
  iterationImages?: IterationImage[];
}

function resolveUrl(url: string): string {
  const base = url.startsWith("http") ? url : `${BACKEND_URL}${url}`;
  const token = getAuthToken();
  if (!token) return base;
  const sep = base.includes("?") ? "&" : "?";
  return `${base}${sep}token=${encodeURIComponent(token)}`;
}

export function ImageResult({ imageUrl, playlistTitle, iterationImages = [] }: Props) {
  const [selectedForDownload, setSelectedForDownload] = useState<string | null>(null);

  const finalUrl = resolveUrl(imageUrl);

  // All images to display: iterations + final
  const allImages = [
    ...iterationImages.map((iter) => ({
      label: `Version ${iter.iteration}`,
      url: resolveUrl(iter.image_url),
    })),
    {
      label: "Final",
      url: finalUrl,
    },
  ];

  // If only one image (no iterations), just show it
  const showGrid = iterationImages.length > 0;
  const downloadTarget = selectedForDownload || finalUrl;

  async function handleDownload(url: string) {
    try {
      const token = getAuthToken();
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `linkedin-${playlistTitle.replace(/[^a-zA-Z0-9]/g, "-")}.png`;
      link.click();
      URL.revokeObjectURL(blobUrl);
    } catch {
      window.open(url, "_blank");
    }
  }

  if (!showGrid) {
    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Generated Image</h3>
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={finalUrl} alt={`LinkedIn summary for: ${playlistTitle}`} className="w-full" />
        </div>
        <button
          onClick={() => handleDownload(finalUrl)}
          className="w-full rounded-lg bg-banana-500 px-4 py-3 font-medium text-white transition-colors hover:bg-banana-600"
        >
          Download Image
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">
        Generated Images
        <span className="ml-2 text-sm font-normal text-gray-500">
          Click an image to select it for download
        </span>
      </h3>

      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(allImages.length, 3)}, 1fr)` }}>
        {allImages.map((img) => (
          <div
            key={img.label}
            onClick={() => setSelectedForDownload(img.url)}
            className={`cursor-pointer overflow-hidden rounded-lg border-2 bg-white shadow-sm transition-all ${
              selectedForDownload === img.url
                ? "border-banana-500 ring-2 ring-banana-200"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <div className="bg-gray-50 px-3 py-1.5 text-center text-xs font-semibold text-gray-600">
              {img.label}
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={img.url}
              alt={`${img.label} - ${playlistTitle}`}
              className="w-full"
            />
          </div>
        ))}
      </div>

      <button
        onClick={() => handleDownload(downloadTarget)}
        className="w-full rounded-lg bg-banana-500 px-4 py-3 font-medium text-white transition-colors hover:bg-banana-600"
      >
        Download {selectedForDownload ? allImages.find((i) => i.url === selectedForDownload)?.label || "Image" : "Final Image"}
      </button>
    </div>
  );
}
