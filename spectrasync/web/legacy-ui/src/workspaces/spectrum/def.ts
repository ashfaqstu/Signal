import { Activity } from "lucide-react";
import { WorkspaceDef } from "../types";

export const spectrumWorkspace: WorkspaceDef = {
  id: "spectrum",
  label: "Spectrum",
  shortcut: "Alt+6",
  icon: Activity,
  previewDefault: true,
  sequence: "never",
  defaultLayout: {
    layout: "1up",
    panes: ["f₁ | f₂"],
  },
  groups: [
    {
      title: "Source",
      params: [
        {
          key: "baseId",
          label: "Image",
          type: "media",
          accept: "image",
        },
        {
          key: "dy",
          label: "Δy",
          type: "number",
          min: -30,
          max: 30,
          step: 0.5,
          default: 12.0,
          unit: "px",
        },
        {
          key: "dx",
          label: "Δx",
          type: "number",
          min: -30,
          max: 30,
          step: 0.5,
          default: -8.0,
          unit: "px",
        },
      ],
    },
  ],
  toRequest: (p) => ({
    baseId: p.baseId || undefined,
    dy: p.dy,
    dx: p.dx,
  }),
};
