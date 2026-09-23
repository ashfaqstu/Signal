import React, { useState, useRef, useEffect } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { Layers, Image as ImageIcon, LineChart } from "lucide-react";
import clsx from "clsx";
import styles from "./Shell.module.css";

import { AppBar } from "./AppBar";
import { ToolBar } from "./ToolBar";
import { StatusBar } from "./StatusBar";
import { ShortcutsModal } from "./ShortcutsModal";
import { DropOverlay } from "./DropOverlay";

import { Viewer } from "../viewer/Viewer";
import { Timeline } from "../timeline/Timeline";
import { StageStrip } from "../workspaces/spectrum/StageStrip";

import { PropertiesPanel } from "../panels/PropertiesPanel";
import { InfoPanel } from "../panels/InfoPanel";
import { LayersPanel } from "../panels/LayersPanel";
import { MediaPanel } from "../panels/MediaPanel";
import { GraphPanel } from "../panels/GraphPanel";

import { useUiStore } from "../state/ui";
import { getWorkspaceDef } from "../workspaces";
import { useImportMedia } from "../api/queries";

export const Shell: React.FC = () => {
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const panelsHidden = useUiStore((s) => s.panelsHidden);
  const togglePanelsHidden = useUiStore((s) => s.togglePanelsHidden);
  const activeRightTab = useUiStore((s) => s.activeRightTab);
  const setActiveRightTab = useUiStore((s) => s.setActiveRightTab);

  const importMutation = useImportMedia();
  const def = getWorkspaceDef(activeWorkspace);
  const isSequenceWorkspace = def.sequence !== "never";

  // Global Tab key to toggle panels
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
        return;
      }
      if (e.key === "Tab") {
        e.preventDefault();
        togglePanelsHidden();
      } else if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setShortcutsOpen(true);
      } else if ((e.ctrlKey || e.metaKey) && (e.key === "o" || e.key === "O")) {
        e.preventDefault();
        fileInputRef.current?.click();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [togglePanelsHidden]);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      importMutation.mutate(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  return (
    <div className={styles.shellContainer}>
      {/* Top App Bar */}
      <AppBar
        onImportClick={() => fileInputRef.current?.click()}
        onOpenShortcuts={() => setShortcutsOpen(true)}
      />

      {/* Main Workspace Area */}
      <div className={styles.mainArea}>
        {!panelsHidden && <ToolBar />}

        <PanelGroup direction="horizontal">
          {/* Center Content Panel */}
          <Panel defaultSize={panelsHidden ? 100 : 75} minSize={30}>
            <div className={styles.centerWorkspaceCol}>
              <div className={styles.viewerContainer}>
                <Viewer />
              </div>

              {activeWorkspace === "spectrum" && (
                <div className={styles.stageStripContainer}>
                  <StageStrip />
                </div>
              )}

              {isSequenceWorkspace && (
                <div className={styles.timelineContainer}>
                  <Timeline />
                </div>
              )}
            </div>
          </Panel>

          {/* Right Dock Panel */}
          {!panelsHidden && (
            <>
              <PanelResizeHandle className={styles.resizeHandleVertical} />
              <Panel defaultSize={25} minSize={18} maxSize={45}>
                <div className={styles.rightDockCol}>
                  <PanelGroup direction="vertical">
                    {/* Top: Properties & Info */}
                    <Panel defaultSize={55} minSize={25}>
                      <div className={styles.rightDockTop}>
                        <PropertiesPanel />
                        <InfoPanel />
                      </div>
                    </Panel>

                    <PanelResizeHandle className={styles.resizeHandleHorizontal} />

                    {/* Bottom: Tabs for Layers, Media, Graph */}
                    <Panel defaultSize={45} minSize={20}>
                      <div className={styles.rightDockBottom}>
                        <div className={styles.rightDockHeader}>
                          <div className={styles.rightTabs}>
                            <button
                              type="button"
                              className={clsx(
                                styles.rightTabBtn,
                                activeRightTab === "layers" && styles.rightTabBtnActive
                              )}
                              onClick={() => setActiveRightTab("layers")}
                              title="Layers"
                            >
                              <Layers size={13} />
                              <span>Layers</span>
                            </button>
                            <button
                              type="button"
                              className={clsx(
                                styles.rightTabBtn,
                                activeRightTab === "media" && styles.rightTabBtnActive
                              )}
                              onClick={() => setActiveRightTab("media")}
                              title="Media"
                            >
                              <ImageIcon size={13} />
                              <span>Media</span>
                            </button>
                            <button
                              type="button"
                              className={clsx(
                                styles.rightTabBtn,
                                activeRightTab === "graph" && styles.rightTabBtnActive
                              )}
                              onClick={() => setActiveRightTab("graph")}
                              title="Graph"
                            >
                              <LineChart size={13} />
                              <span>Graph</span>
                            </button>
                          </div>
                        </div>

                        <div className={styles.rightDockBody}>
                          {activeRightTab === "layers" && <LayersPanel />}
                          {activeRightTab === "media" && (
                            <MediaPanel onImportClick={() => fileInputRef.current?.click()} />
                          )}
                          {activeRightTab === "graph" && <GraphPanel />}
                        </div>
                      </div>
                    </Panel>
                  </PanelGroup>
                </div>
              </Panel>
            </>
          )}
        </PanelGroup>
      </div>

      {/* Bottom Status Bar */}
      <StatusBar />

      {/* Hidden File Input for Imports */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        multiple
        accept="image/*,video/*"
        style={{ display: "none" }}
      />

      {/* Modals & Overlays */}
      <ShortcutsModal isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      <DropOverlay />
    </div>
  );
};
