"use client";

const PHASES = [
  { key: "scraping", label: "Scraping playlist" },
  { key: "planning", label: "Planning visual" },
  { key: "generating", label: "Generating image" },
  { key: "refining", label: "Refining quality" },
  { key: "captioning", label: "Writing caption" },
  { key: "complete", label: "Complete" },
] as const;

interface Props {
  currentPhase: string;
  message: string;
  progress: number;
}

export function ProgressTracker({ currentPhase, message, progress }: Props) {
  const currentIndex = PHASES.findIndex((p) => p.key === currentPhase);

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">
            {message || "Starting..."}
          </span>
          <span className="text-gray-500">
            {Math.round(progress * 100)}%
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
          <div
            className="h-full rounded-full bg-banana-500 transition-all duration-500 ease-out"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      </div>

      {/* Phase indicators */}
      <div className="flex justify-between">
        {PHASES.map((phase, i) => {
          const isActive = phase.key === currentPhase;
          const isDone = i < currentIndex;
          return (
            <div key={phase.key} className="flex flex-col items-center gap-1">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all ${
                  isDone
                    ? "bg-green-500 text-white"
                    : isActive
                      ? "bg-banana-500 text-white animate-pulse"
                      : "bg-gray-200 text-gray-400"
                }`}
              >
                {isDone ? "\u2713" : i + 1}
              </div>
              <span
                className={`text-xs ${
                  isActive
                    ? "font-medium text-banana-600"
                    : isDone
                      ? "text-green-600"
                      : "text-gray-400"
                }`}
              >
                {phase.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
