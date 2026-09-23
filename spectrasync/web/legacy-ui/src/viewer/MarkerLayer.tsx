import React from "react";
import { Marker } from "../api/types";

export interface MarkerLayerProps {
  markers: Marker[];
  layerName: string;
  width: number;
  height: number;
}

export const MarkerLayer: React.FC<MarkerLayerProps> = ({
  markers,
  layerName,
  width,
  height,
}) => {
  const matchingMarkers = markers.filter(
    (m) => m.layer === layerName || (m.layer.startsWith("overlay#") && layerName.toLowerCase().includes("overlay"))
  );

  if (matchingMarkers.length === 0) return null;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    >
      {matchingMarkers.map((m, idx) => {
        if (m.type === "crosshair") {
          const arm = Math.max(width, height) * 0.04;
          const radius = Math.max(width, height) * 0.035;
          return (
            <g key={idx}>
              <circle
                cx={m.x}
                cy={m.y}
                r={radius}
                fill="none"
                stroke="var(--accent)"
                strokeWidth={1.5}
                vectorEffect="non-scaling-stroke"
              />
              <line
                x1={m.x - arm}
                y1={m.y}
                x2={m.x + arm}
                y2={m.y}
                stroke="var(--accent)"
                strokeWidth={1.5}
                vectorEffect="non-scaling-stroke"
              />
              <line
                x1={m.x}
                y1={m.y - arm}
                x2={m.x}
                y2={m.y + arm}
                stroke="var(--accent)"
                strokeWidth={1.5}
                vectorEffect="non-scaling-stroke"
              />
            </g>
          );
        }

        if (m.type === "box") {
          return (
            <rect
              key={idx}
              x={m.x}
              y={m.y}
              width={m.w || 20}
              height={m.h || 20}
              fill="none"
              stroke="var(--warn)"
              strokeWidth={1.5}
              vectorEffect="non-scaling-stroke"
            />
          );
        }

        return null;
      })}
    </svg>
  );
};
