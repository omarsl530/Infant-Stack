import { useMemo, useRef, useState, useEffect, useCallback } from "react";
import type { RTLSPosition, Zone, Gate, Floorplan, Alert } from "../types";

interface FloorplanMapProps {
  floorplan: Floorplan | null;
  positions: RTLSPosition[];
  gates: Gate[];
  zones: Zone[];
  alerts?: Alert[]; // Added alerts prop
  selectedTagId?: string | null;
  showHeatmap?: boolean;
  onTagClick?: (position: RTLSPosition) => void;
  onGateClick?: (gate: Gate) => void;
  onZoneClick?: (zone: Zone) => void;
}

export function FloorplanMap({
  floorplan,
  positions,
  gates,
  zones,
  alerts = [], // Default to empty array
  selectedTagId,
  showHeatmap = false,
  onTagClick,
  onGateClick,
  onZoneClick,
}: FloorplanMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [_containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  // Handle container resize
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setContainerSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Convert world coordinates to screen coordinates
  const worldToScreen = useCallback(
    (x: number, y: number) => {
      if (!floorplan) return { x: 0, y: 0 };
      const screenX =
        (x - floorplan.originX) * floorplan.scale * scale + offset.x;
      const screenY =
        (y - floorplan.originY) * floorplan.scale * scale + offset.y;
      return { x: screenX, y: screenY };
    },
    [floorplan, scale, offset],
  );

  // Handle mouse wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setScale((prev) => Math.min(Math.max(prev * delta, 0.5), 4));
  }, []);

  // Handle pan start
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      setIsDragging(true);
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    },
    [offset],
  );

  // Handle pan move
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    },
    [isDragging, dragStart],
  );

  // Handle pan end
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // --- Touch Support ---
  const lastTouchDistance = useRef<number | null>(null);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length === 1) {
        setIsDragging(true);
        const touch = e.touches[0];
        setDragStart({
          x: touch.clientX - offset.x,
          y: touch.clientY - offset.y,
        });
        lastTouchDistance.current = null;
      } else if (e.touches.length === 2) {
        setIsDragging(false); // Disable panning during pinch
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY,
        );
        lastTouchDistance.current = dist;
      }
    },
    [offset],
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length === 1 && isDragging) {
        const touch = e.touches[0];
        setOffset({
          x: touch.clientX - dragStart.x,
          y: touch.clientY - dragStart.y,
        });
      } else if (e.touches.length === 2 && lastTouchDistance.current !== null) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY,
        );

        const delta = dist / lastTouchDistance.current;
        setScale((prev) => Math.min(Math.max(prev * delta, 0.5), 4));
        lastTouchDistance.current = dist;
      }
    },
    [isDragging, dragStart],
  );

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
    lastTouchDistance.current = null;
  }, []);

  // Reset view
  const handleReset = useCallback(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  }, []);

  // Tag marker color based on asset type and status
  const getTagColor = useCallback((position: RTLSPosition) => {
    if (position.batteryPct < 20) return "bg-amber-500";
    switch (position.assetType) {
      case "infant":
        return "bg-cyan-500";
      case "mother":
        return "bg-pink-500";
      case "staff":
        return "bg-purple-500";
      default:
        return "bg-slate-400";
    }
  }, []);

  // Render zones
  const renderedZones = useMemo(() => {
    return zones.map((zone) => {
      const points = zone.polygon
        .map((p) => {
          const screen = worldToScreen(p.x, p.y);
          return `${screen.x},${screen.y}`;
        })
        .join(" ");

      const zoneClass =
        zone.type === "restricted"
          ? "zone-restricted"
          : zone.type === "exit"
            ? "zone-exit"
            : "zone-authorized";

      return (
        <polygon
          key={zone.id}
          points={points}
          className={`${zoneClass} cursor-pointer hover:opacity-80 transition-opacity`}
          onClick={() => onZoneClick?.(zone)}
        />
      );
    });
  }, [zones, worldToScreen, onZoneClick]);

  // Render gates
  const renderedGates = useMemo(() => {
    return gates.map((gate) => {
      // Use position from gate data (assuming stored as metadata)
      const x = 50 + gates.indexOf(gate) * 100; // Placeholder positioning
      const y = 50;
      const screen = worldToScreen(x, y);

      const stateClass =
        gate.state === "FORCED_OPEN"
          ? "gate-forced"
          : gate.state === "OPEN" || gate.state === "HELD_OPEN"
            ? "gate-open"
            : "gate-closed";

      return (
        <div
          key={gate.id}
          className={`gate-marker ${stateClass} cursor-pointer hover:scale-110 transition-transform flex items-center justify-center text-xs font-bold`}
          style={{ left: screen.x, top: screen.y }}
          onClick={() => onGateClick?.(gate)}
          title={`${gate.name}: ${gate.state}`}
        >
          {gate.state === "FORCED_OPEN"
            ? "!"
            : gate.state === "OPEN"
              ? "O"
              : "C"}
        </div>
      );
    });
  }, [gates, worldToScreen, onGateClick]);

  // Render tag markers
  const renderedTags = useMemo(() => {
    return positions.map((position) => {
      const screen = worldToScreen(position.x, position.y);
      const isSelected = selectedTagId === position.tagId;
      const tagColor = getTagColor(position);

      // Check for active alerts for this tag
      const hasActiveAlert = alerts.some(
        (a) => a.tagId === position.tagId && !a.acknowledged,
      );
      const alertClass = hasActiveAlert
        ? "animate-pulse ring-2 ring-red-500 ring-offset-2"
        : "";

      return (
        <div
          key={position.tagId}
          className={`tag-marker ${tagColor} cursor-pointer hover:scale-125 transition-transform ${
            isSelected
              ? "ring-2 ring-white ring-offset-2 ring-offset-slate-900 z-10"
              : ""
          } ${position.batteryPct < 20 ? "tag-marker-alert" : ""} ${alertClass}`}
          style={{
            left: screen.x,
            top: screen.y,
            width: isSelected || hasActiveAlert ? "20px" : "14px",
            height: isSelected || hasActiveAlert ? "20px" : "14px",
          }}
          onClick={() => onTagClick?.(position)}
          title={`${position.tagId} (${position.assetType})${hasActiveAlert ? " - ALERT" : ""}`}
        >
          {isSelected && (
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 px-2 py-1 rounded text-xs whitespace-nowrap">
              {position.tagId}
            </div>
          )}
        </div>
      );
    });
  }, [
    positions,
    worldToScreen,
    selectedTagId,
    getTagColor,
    onTagClick,
    alerts,
  ]);

  // Render heatmap overlay (simplified)
  const heatmapOverlay = useMemo(() => {
    if (!showHeatmap || positions.length === 0) return null;

    // Group positions into grid cells for density calculation
    const gridSize = 50;
    const density: Record<string, number> = {};

    positions.forEach((pos) => {
      const screen = worldToScreen(pos.x, pos.y);
      const cellX = Math.floor(screen.x / gridSize);
      const cellY = Math.floor(screen.y / gridSize);
      const key = `${cellX},${cellY}`;
      density[key] = (density[key] || 0) + 1;
    });

    const maxDensity = Math.max(...Object.values(density));

    return Object.entries(density).map(([key, count]) => {
      const [cellX, cellY] = key.split(",").map(Number);
      const opacity = (count / maxDensity) * 0.5;
      return (
        <div
          key={key}
          className="absolute bg-red-500 rounded-full blur-xl pointer-events-none"
          style={{
            left: cellX * gridSize + gridSize / 2,
            top: cellY * gridSize + gridSize / 2,
            width: gridSize * 2,
            height: gridSize * 2,
            opacity,
            transform: "translate(-50%, -50%)",
          }}
        />
      );
    });
  }, [showHeatmap, positions, worldToScreen]);

  if (!floorplan) {
    return (
      <div className="floorplan-container flex items-center justify-center h-full min-h-[400px]">
        <div className="text-center text-slate-400">
          <p className="text-lg font-medium">No Floorplan Selected</p>
          <p className="text-sm mt-2">Select a floor to view the map</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="floorplan-container relative h-full min-h-[500px] select-none"
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      style={{ cursor: isDragging ? "grabbing" : "grab", touchAction: "none" }}
    >
      {/* Floorplan Image */}
      <img
        src={floorplan.imageUrl}
        alt={floorplan.name}
        className="absolute pointer-events-none"
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "0 0",
          left: offset.x,
          top: offset.y,
        }}
        draggable={false}
      />

      {/* SVG Overlay for Zones */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ overflow: "visible" }}
      >
        <g className="pointer-events-auto">{renderedZones}</g>
      </svg>

      {/* Heatmap Overlay */}
      {heatmapOverlay}

      {/* Gate Markers */}
      {renderedGates}

      {/* Tag Markers */}
      {renderedTags}

      {/* Map Controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2">
        <button
          onClick={() => setScale((s) => Math.min(s * 1.2, 4))}
          className="w-10 h-10 bg-slate-800/80 hover:bg-slate-700 rounded-lg flex items-center justify-center text-lg font-bold transition-colors"
        >
          +
        </button>
        <button
          onClick={() => setScale((s) => Math.max(s * 0.8, 0.5))}
          className="w-10 h-10 bg-slate-800/80 hover:bg-slate-700 rounded-lg flex items-center justify-center text-lg font-bold transition-colors"
        >
          −
        </button>
        <button
          onClick={handleReset}
          className="w-10 h-10 bg-slate-800/80 hover:bg-slate-700 rounded-lg flex items-center justify-center text-xs font-medium transition-colors"
          title="Reset View"
        >
          ⟲
        </button>
      </div>

      {/* Legend */}
      <div className="absolute top-4 left-4 bg-slate-800/90 rounded-lg p-3 text-xs space-y-2">
        <div className="font-medium text-slate-300 mb-2">Legend</div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-cyan-500" />
          <span>Infant</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-pink-500" />
          <span>Mother</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-purple-500" />
          <span>Staff</span>
        </div>
        <div className="flex items-center gap-2 pt-2 border-t border-slate-700">
          <div className="w-4 h-4 rounded bg-emerald-500/80" />
          <span>Gate Open</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-slate-600/80" />
          <span>Gate Closed</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-red-500" />
          <span>Forced/Alert</span>
        </div>
      </div>

      {/* Connection Status */}
      <div className="absolute top-4 right-4 flex items-center gap-2 bg-slate-800/90 rounded-lg px-3 py-2 text-xs">
        <div
          className={`w-2 h-2 rounded-full ${positions.length > 0 ? "status-online" : "status-offline"}`}
        />
        <span>{positions.length} tags</span>
      </div>
    </div>
  );
}

export default FloorplanMap;
