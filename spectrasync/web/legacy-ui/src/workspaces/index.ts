import { alignWorkspace } from "./align/def";
import { rotateWorkspace } from "./rotate/def";
import { stackWorkspace } from "./stack/def";
import { removeWorkspace } from "./remove/def";
import { highlightWorkspace } from "./highlight/def";
import { spectrumWorkspace } from "./spectrum/def";
import { WorkspaceDef } from "./types";

export const WORKSPACES: WorkspaceDef[] = [
  alignWorkspace,
  rotateWorkspace,
  stackWorkspace,
  removeWorkspace,
  highlightWorkspace,
  spectrumWorkspace,
];

export function getWorkspaceDef(id: string): WorkspaceDef {
  return WORKSPACES.find((w) => w.id === id) || WORKSPACES[0];
}
