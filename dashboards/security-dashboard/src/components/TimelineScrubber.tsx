import { useState, useEffect } from 'react';
import { PlayIcon, PauseIcon, ForwardIcon, BackwardIcon } from '@heroicons/react/24/solid';
import { ArrowPathIcon, SignalIcon } from '@heroicons/react/24/outline';

interface TimelineScrubberProps {
  isLive: boolean;
  isPlaying: boolean;
  currentTime: Date;
  startTime: Date;
  endTime: Date;
  playbackSpeed: number;
  onToggleLive: () => void;
  onTogglePlay: () => void;
  onSeek: (time: Date) => void;
  onSpeedChange: (speed: number) => void;
  onExport?: () => void;
  onRangeChange?: (start: Date, end: Date) => void;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

// Helper to format Date for datetime-local input
const toLocalISO = (date: Date) => {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

export function TimelineScrubber({
  isLive,
  isPlaying,
  currentTime,
  startTime,
  endTime,
  playbackSpeed,
  onToggleLive,
  onTogglePlay,
  onSeek,
  onSpeedChange,
  onExport,
  onRangeChange,
}: TimelineScrubberProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState(0);

  const totalDuration = endTime.getTime() - startTime.getTime();
  const currentProgress = ((currentTime.getTime() - startTime.getTime()) / totalDuration) * 100;

  const handleTrackClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const position = (e.clientX - rect.left) / rect.width;
    const newTime = new Date(startTime.getTime() + position * totalDuration);
    onSeek(newTime);
  };

  const handleMouseDown = (_e: React.MouseEvent) => {
    setIsDragging(true);
    document.body.style.cursor = 'grabbing';
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;
    const track = document.querySelector('.timeline-track') as HTMLElement;
    if (!track) return;
    
    const rect = track.getBoundingClientRect();
    const position = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setDragPosition(position * 100);
    
    const newTime = new Date(startTime.getTime() + position * totalDuration);
    onSeek(newTime);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    document.body.style.cursor = '';
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging]);

  const speedOptions = [0.5, 1, 2, 5, 10];

  return (
    <div className="timeline-container">
      <div className="flex flex-wrap items-center justify-between mb-4 gap-4">
        {/* Left: Time Controls */}
        <div className="flex items-center gap-4">
            <div className="flex flex-col gap-1">
                <span className="text-xs text-slate-400">Range Start</span>
                <input 
                    type="datetime-local"
                    className="bg-slate-800 border-none rounded text-xs text-slate-300 py-1"
                    value={toLocalISO(startTime)}
                    onChange={(e) => {
                        if (onRangeChange && e.target.value) {
                            onRangeChange(new Date(e.target.value), endTime);
                        }
                    }}
                />
            </div>
            <span className="text-slate-500">to</span>
            <div className="flex flex-col gap-1">
                <span className="text-xs text-slate-400">Range End</span>
                <input 
                    type="datetime-local"
                    className="bg-slate-800 border-none rounded text-xs text-slate-300 py-1"
                    value={toLocalISO(endTime)}
                    onChange={(e) => {
                        if (onRangeChange && e.target.value) {
                            onRangeChange(startTime, new Date(e.target.value));
                        }
                    }}
                />
            </div>
        </div>

        {/* Center: Controls */}
        <div className="flex items-center gap-2">
          {/* Step backward */}
          <button
            onClick={() => onSeek(new Date(currentTime.getTime() - 10000))}
            className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 transition-colors"
            title="Back 10s"
            disabled={isLive}
          >
            <BackwardIcon className="w-4 h-4" />
          </button>

          {/* Play/Pause */}
          <button
            onClick={onTogglePlay}
            className="p-3 rounded-full bg-blue-600 hover:bg-blue-700 transition-colors"
            disabled={isLive}
          >
            {isPlaying ? (
              <PauseIcon className="w-5 h-5" />
            ) : (
              <PlayIcon className="w-5 h-5" />
            )}
          </button>

          {/* Step forward */}
          <button
            onClick={() => onSeek(new Date(currentTime.getTime() + 10000))}
            className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 transition-colors"
            title="Forward 10s"
            disabled={isLive}
          >
            <ForwardIcon className="w-4 h-4" />
          </button>

          {/* Speed selector */}
          <select
            value={playbackSpeed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            className="px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm"
            disabled={isLive}
          >
            {speedOptions.map((speed) => (
              <option key={speed} value={speed}>
                {speed}x
              </option>
            ))}
          </select>
        </div>

        {/* Right: Mode toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggleLive}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              isLive
                ? 'bg-red-600 text-white'
                : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50'
            }`}
          >
            {isLive ? (
              <>
                <SignalIcon className="w-4 h-4" />
                <span>LIVE</span>
                <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
              </>
            ) : (
              <>
                <ArrowPathIcon className="w-4 h-4" />
                <span>GO LIVE</span>
              </>
            )}
          </button>

          {onExport && (
            <button
              onClick={onExport}
              className="px-4 py-2 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 text-sm font-medium transition-colors"
            >
              Export
            </button>
          )}
        </div>
      </div>

      {/* Timeline track */}
      <div 
        className="timeline-track relative cursor-pointer"
        onClick={handleTrackClick}
      >
        <div
          className="timeline-progress"
          style={{ width: `${isDragging ? dragPosition : currentProgress}%` }}
        />
        <div
          className="timeline-thumb"
          style={{ left: `${isDragging ? dragPosition : currentProgress}%` }}
          onMouseDown={handleMouseDown}
        />
      </div>

      {/* Time labels */}
      <div className="flex justify-between mt-2 text-xs text-slate-500">
        <span>{formatTime(startTime)}</span>
        <span>{formatTime(endTime)}</span>
      </div>
    </div>
  );
}

export default TimelineScrubber;
