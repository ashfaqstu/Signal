import React from "react";

export type Param =
  | {
      key: string;
      label: string;
      type: "number";
      min: number;
      max: number;
      step: number;
      default: number;
      unit?: string;
      decimals?: number;
      when?: (p: any) => boolean;
    }
  | {
      key: string;
      label: string;
      type: "choice";
      options: { value: string; label: string }[];
      default: string;
      when?: (p: any) => boolean;
      display?: "segmented" | "select";
    }
  | {
      key: string;
      label: string;
      type: "registry";
      registry: "window" | "subpixel" | "reducer" | "detector" | "overlay" | "filter";
      default: string;
      when?: (p: any) => boolean;
    }
  | {
      key: string;
      label: string;
      type: "toggle";
      default: boolean;
      when?: (p: any) => boolean;
    }
  | {
      key: string;
      label: string;
      type: "media";
      accept: "image" | "video";
      when?: (p: any) => boolean;
    }
  | {
      key: string;
      label: string;
      type: "mediaMany";
      accept: "image";
      min?: number;
      when?: (p: any) => boolean;
    };

export interface WorkspaceDef {
  id: "align" | "rotate" | "stack" | "remove" | "highlight" | "spectrum";
  label: string;
  shortcut: string;
  icon: React.ComponentType<any>;
  groups: { title: "Source" | "Method" | "Detection" | "Display"; params: Param[] }[];
  sequence: "always" | "whenVideo" | "never";
  previewDefault: boolean;
  defaultLayout: { layout: "1up" | "2up" | "4up" | "split"; panes: string[] };
  frameLayer?: string;
  toRequest: (p: any) => any;
}
