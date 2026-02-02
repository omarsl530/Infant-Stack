import { useState, useEffect, useCallback } from "react";
import {
  VideoCameraIcon,
  XMarkIcon,
  ArrowsPointingOutIcon,
  SignalSlashIcon,
} from "@heroicons/react/24/outline";
import type { Camera, Gate } from "../types";
import { getCameraSnapshot } from "../api";

interface CameraGridProps {
  cameras: Camera[];
  gates?: Gate[];
  columns?: 2 | 3 | 4;
  refreshInterval?: number;
  onCameraClick?: (camera: Camera) => void;
}

interface CameraThumbnailProps {
  camera: Camera;
  refreshInterval: number;
  onClick?: () => void;
}

function CameraThumbnail({
  camera,
  refreshInterval,
  onClick,
}: CameraThumbnailProps) {
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadThumbnail = useCallback(async () => {
    try {
      const url = await getCameraSnapshot(camera.cameraId);
      // Revoke previous URL to prevent memory leaks
      if (thumbnailUrl) {
        URL.revokeObjectURL(thumbnailUrl);
      }
      setThumbnailUrl(url);
      setError(null);
    } catch (err) {
      setError("Failed to load");
    } finally {
      setIsLoading(false);
    }
  }, [camera.cameraId]);

  useEffect(() => {
    loadThumbnail();
    const interval = setInterval(loadThumbnail, refreshInterval);
    return () => {
      clearInterval(interval);
      if (thumbnailUrl) {
        URL.revokeObjectURL(thumbnailUrl);
      }
    };
  }, [loadThumbnail, refreshInterval]);

  return (
    <div
      className="relative aspect-video bg-slate-800 rounded-lg overflow-hidden cursor-pointer group"
      onClick={onClick}
    >
      {isLoading && !thumbnailUrl ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-slate-600 border-t-blue-500 rounded-full animate-spin" />
        </div>
      ) : error || camera.status === "offline" ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500">
          <SignalSlashIcon className="w-8 h-8 mb-2" />
          <span className="text-xs">{error || "Offline"}</span>
        </div>
      ) : thumbnailUrl ? (
        <img
          src={thumbnailUrl}
          alt={camera.name}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-700 to-slate-800">
          <VideoCameraIcon className="w-12 h-12 text-slate-600" />
        </div>
      )}

      {/* Overlay on hover */}
      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
        <ArrowsPointingOutIcon className="w-8 h-8 text-white" />
      </div>

      {/* Camera name label */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
        <p className="text-xs font-medium truncate">{camera.name}</p>
        <p className="text-xs text-slate-400 truncate">
          {camera.zone || camera.floor}
        </p>
      </div>

      {/* Status indicator */}
      <div
        className={`absolute top-2 right-2 w-2 h-2 rounded-full ${
          camera.status === "online"
            ? "status-online"
            : camera.status === "error"
              ? "status-alert"
              : "status-offline"
        }`}
      />
    </div>
  );
}

export function CameraGrid({
  cameras,
  gates: _gates,
  columns = 2,
  refreshInterval = 5000,
  onCameraClick,
}: CameraGridProps) {
  // Sort cameras to show gate cameras first
  const sortedCameras = [...cameras].sort((a, b) => {
    const aHasGate = a.gateId ? 1 : 0;
    const bHasGate = b.gateId ? 1 : 0;
    return bHasGate - aHasGate;
  });

  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4",
  };

  return (
    <div className={`grid ${gridCols[columns]} gap-3`}>
      {sortedCameras.map((camera) => (
        <CameraThumbnail
          key={camera.id}
          camera={camera}
          refreshInterval={refreshInterval}
          onClick={onCameraClick ? () => onCameraClick(camera) : undefined}
        />
      ))}
    </div>
  );
}

// Camera Stream Modal
interface CameraStreamModalProps {
  camera: Camera | null;
  onClose: () => void;
}

export function CameraStreamModal({ camera, onClose }: CameraStreamModalProps) {
  if (!camera) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-slate-900 rounded-2xl border border-slate-700 shadow-2xl w-full max-w-4xl mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <VideoCameraIcon className="w-5 h-5 text-blue-400" />
            <div>
              <h3 className="font-semibold">{camera.name}</h3>
              <p className="text-sm text-slate-400">
                {camera.zone} • {camera.floor}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700 transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Video container */}
        <div className="aspect-video bg-black">
          {camera.status === "online" ? (
            <video
              src={camera.streamUrl}
              autoPlay
              controls
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-slate-500">
              <SignalSlashIcon className="w-16 h-16 mb-4" />
              <p className="text-lg font-medium">Camera Offline</p>
              <p className="text-sm mt-1">Unable to connect to stream</p>
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="p-4 border-t border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                camera.status === "online" ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
            <span className="text-sm text-slate-400">
              {camera.status === "online" ? "Live" : "Offline"}
            </span>
          </div>
          <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-medium transition-colors">
            Download Snapshot
          </button>
        </div>
      </div>
    </div>
  );
}

export default CameraGrid;
