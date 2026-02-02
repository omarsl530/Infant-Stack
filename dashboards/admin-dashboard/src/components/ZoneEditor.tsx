import React, { useState, useEffect, useRef, MouseEvent } from "react";
import { PlusIcon, TrashIcon } from "@heroicons/react/24/outline";
import { Zone, ZoneCreate } from "../types";
import { fetchZones, createZone, deleteZone } from "../api";

const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 600;
const GRID_SIZE = 40;

const ZoneEditor: React.FC = () => {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeFloor, setActiveFloor] = useState("F1");
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  // Drawing State
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentPolygon, setCurrentPolygon] = useState<
    { x: number; y: number }[]
  >([]);
  const [drawingType, setDrawingType] = useState<
    "authorized" | "restricted" | "exit"
  >("restricted");
  const [newZoneName, setNewZoneName] = useState("");

  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    loadZones();
  }, [activeFloor]);

  useEffect(() => {
    drawCanvas();
  }, [zones, currentPolygon, selectedZoneId]);

  const loadZones = async () => {
    setLoading(true);
    try {
      const data = await fetchZones(activeFloor);
      setZones(data.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const drawCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear
    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

    if (loading) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "14px sans-serif";
      ctx.fillText("Loading zones...", 20, 30);
      return;
    }

    // Draw Grid
    ctx.strokeStyle = "#334155"; // Slate-700
    ctx.lineWidth = 1;
    for (let x = 0; x <= CANVAS_WIDTH; x += GRID_SIZE) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, CANVAS_HEIGHT);
      ctx.stroke();
    }
    for (let y = 0; y <= CANVAS_HEIGHT; y += GRID_SIZE) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(CANVAS_WIDTH, y);
      ctx.stroke();
    }

    // Draw Existing Zones
    zones.forEach((zone) => {
      if (!zone.polygon || zone.polygon.length === 0) return;

      ctx.beginPath();
      ctx.moveTo(zone.polygon[0].x, zone.polygon[0].y);
      for (let i = 1; i < zone.polygon.length; i++) {
        ctx.lineTo(zone.polygon[i].x, zone.polygon[i].y);
      }
      ctx.closePath();

      // Style based on type
      if (zone.id === selectedZoneId) {
        ctx.lineWidth = 3;
        ctx.strokeStyle = "#fff";
      } else {
        ctx.lineWidth = 2;
        ctx.strokeStyle = zone.color || getColorForType(zone.zone_type);
      }

      ctx.fillStyle = (zone.color || getColorForType(zone.zone_type)) + "40"; // Transparent fill
      ctx.fill();
      ctx.stroke();

      // Label
      ctx.fillStyle = "#fff";
      ctx.font = "12px sans-serif";
      ctx.fillText(zone.name, zone.polygon[0].x, zone.polygon[0].y - 5);
    });

    // Draw Current Polygon (Being drawn)
    if (currentPolygon.length > 0) {
      ctx.beginPath();
      ctx.moveTo(currentPolygon[0].x, currentPolygon[0].y);
      for (let i = 1; i < currentPolygon.length; i++) {
        ctx.lineTo(currentPolygon[i].x, currentPolygon[i].y);
      }
      // If closing loop visuals can differ, but keeping it open
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#fbbf24"; // Amber-400
      ctx.stroke();

      // Draw points
      currentPolygon.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = "#fbbf24";
        ctx.fill();
      });
    }
  };

  const getColorForType = (type: string) => {
    switch (type) {
      case "restricted":
        return "#ef4444"; // Red-500
      case "authorized":
        return "#22c55e"; // Green-500
      case "exit":
        return "#3b82f6"; // Blue-500
      default:
        return "#94a3b8";
    }
  };

  const handleCanvasClick = (e: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Snap to grid (optional, simpler for demo)
    // const snappedX = Math.round(x / 10) * 10;
    // const snappedY = Math.round(y / 10) * 10;

    setCurrentPolygon([...currentPolygon, { x, y }]);
  };

  const handleFinishDrawing = async () => {
    if (currentPolygon.length < 3) {
      alert("A zone must have at least 3 points");
      return;
    }
    if (!newZoneName) {
      alert("Please enter a zone name");
      return;
    }

    try {
      const newZone: ZoneCreate = {
        name: newZoneName,
        floor: activeFloor,
        zone_type: drawingType,
        polygon: currentPolygon,
        color: getColorForType(drawingType),
      };

      const created = await createZone(newZone);
      setZones([...zones, created]);

      // Reset
      setIsDrawing(false);
      setCurrentPolygon([]);
      setNewZoneName("");
    } catch (err) {
      console.error("Failed to create zone", err);
    }
  };

  const handleDeleteZone = async () => {
    if (!selectedZoneId) return;
    if (!confirm("Are you sure you want to delete this zone?")) return;

    try {
      await deleteZone(selectedZoneId);
      setZones(zones.filter((z) => z.id !== selectedZoneId));
      setSelectedZoneId(null);
    } catch (err) {
      console.error("Failed to delete zone", err);
    }
  };

  return (
    <div className="flex h-[calc(100vh-12rem)] gap-4">
      {/* Sidebar Controls */}
      <div className="w-64 flex flex-col gap-4">
        {/* Floor Selection */}
        <div className="glass-card p-4">
          <label className="form-label">Floor</label>
          <select
            value={activeFloor}
            onChange={(e) => setActiveFloor(e.target.value)}
            className="form-select"
          >
            <option value="F1">First Floor</option>
            <option value="F2">Second Floor</option>
            <option value="F3">Third Floor</option>
          </select>
        </div>

        {/* Drawing Controls */}
        <div className="glass-card p-4 flex-1 flex flex-col">
          <h3 className="font-medium text-white mb-4">Zone Controls</h3>

          {!isDrawing ? (
            <button
              onClick={() => setIsDrawing(true)}
              className="btn-primary w-full mb-4"
            >
              <PlusIcon className="w-5 h-5 mr-2" />
              New Zone
            </button>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="form-label">Name</label>
                <input
                  type="text"
                  value={newZoneName}
                  onChange={(e) => setNewZoneName(e.target.value)}
                  className="form-input"
                  placeholder="Zone Name"
                />
              </div>
              <div>
                <label className="form-label">Type</label>
                <select
                  value={drawingType}
                  onChange={(e) => setDrawingType(e.target.value as any)}
                  className="form-select"
                >
                  <option value="restricted">Restricted (Red)</option>
                  <option value="authorized">Authorized (Green)</option>
                  <option value="exit">Exit (Blue)</option>
                </select>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleFinishDrawing}
                  className="btn-primary flex-1"
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setIsDrawing(false);
                    setCurrentPolygon([]);
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
              <p className="text-xs text-slate-400">
                Click on canvas to place points.
              </p>
            </div>
          )}

          {/* Zone List */}
          <div className="mt-6 flex-1 overflow-y-auto">
            <h4 className="text-sm font-medium text-slate-400 mb-2">
              Existing Zones
            </h4>
            <div className="space-y-2">
              {zones.map((zone) => (
                <div
                  key={zone.id}
                  onClick={() => setSelectedZoneId(zone.id)}
                  className={`p-2 rounded cursor-pointer border transition-colors flex justify-between items-center
                     ${
                       selectedZoneId === zone.id
                         ? "bg-slate-700 border-indigo-500"
                         : "bg-slate-800/50 border-transparent hover:bg-slate-700"
                     }`}
                >
                  <div>
                    <div className="font-medium text-white text-sm">
                      {zone.name}
                    </div>
                    <div className="text-xs text-slate-400 capitalize">
                      {zone.zone_type}
                    </div>
                  </div>
                </div>
              ))}
              {zones.length === 0 && (
                <p className="text-slate-500 text-sm">No zones yet.</p>
              )}
            </div>
          </div>

          {selectedZoneId && (
            <button
              onClick={handleDeleteZone}
              className="btn-danger w-full mt-4"
            >
              <TrashIcon className="w-4 h-4 mr-2" />
              Delete Selected
            </button>
          )}
        </div>
      </div>

      {/* Canvas Area */}
      <div className="flex-1 glass-card p-4 flex items-center justify-center bg-slate-900/50 overflow-auto">
        <canvas
          ref={canvasRef}
          width={CANVAS_WIDTH}
          height={CANVAS_HEIGHT}
          onClick={handleCanvasClick}
          className="cursor-crosshair bg-slate-900 border border-slate-700 shadow-lg rounded"
        />
      </div>
    </div>
  );
};

export default ZoneEditor;
