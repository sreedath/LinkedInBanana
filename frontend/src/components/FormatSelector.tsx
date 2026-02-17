"use client";

interface Props {
  value: "landscape" | "square";
  onChange: (format: "landscape" | "square") => void;
  disabled?: boolean;
}

export function FormatSelector({ value, onChange, disabled }: Props) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Image Format
      </label>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => onChange("landscape")}
          disabled={disabled}
          className={`flex-1 rounded-lg border-2 p-4 text-center transition-all ${
            value === "landscape"
              ? "border-banana-500 bg-banana-50"
              : "border-gray-200 hover:border-gray-300"
          } disabled:opacity-50`}
        >
          <div
            className={`mx-auto mb-2 h-8 w-14 rounded border-2 ${
              value === "landscape"
                ? "border-banana-500 bg-banana-100"
                : "border-gray-300 bg-gray-100"
            }`}
          />
          <div className="text-sm font-medium">Landscape</div>
          <div className="text-xs text-gray-500">1200 x 627</div>
        </button>
        <button
          type="button"
          onClick={() => onChange("square")}
          disabled={disabled}
          className={`flex-1 rounded-lg border-2 p-4 text-center transition-all ${
            value === "square"
              ? "border-banana-500 bg-banana-50"
              : "border-gray-200 hover:border-gray-300"
          } disabled:opacity-50`}
        >
          <div
            className={`mx-auto mb-2 h-10 w-10 rounded border-2 ${
              value === "square"
                ? "border-banana-500 bg-banana-100"
                : "border-gray-300 bg-gray-100"
            }`}
          />
          <div className="text-sm font-medium">Square</div>
          <div className="text-xs text-gray-500">1080 x 1080</div>
        </button>
      </div>
    </div>
  );
}
