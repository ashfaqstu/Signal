import React from "react";
import clsx from "clsx";
import { LayoutGrid, Columns, Square, SplitSquareVertical } from "lucide-react";
import styles from "./Viewer.module.css";
import { useUiStore } from "../state/ui";
import { useParamsStore } from "../state/params";
import { useTimelineStore } from "../state/timeline";
import { Pane } from "./Pane";
import { SplitCompare } from "./SplitCompare";
import { StageStrip } from "../workspaces/spectrum/StageStrip";
import { Button } from "../controls/Button";
import { IconButton } from "../controls/IconButton";
import { Select } from "../controls/Select";

export interface ViewerProps {
  onProbeClick?: (x: number, y: number) => void;
  onImportClick?: () => void;
}

export const Viewer: React.FC<ViewerProps> = ({ onProbeClick, onImportClick }) => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const layout = useUiStore((s) => s.layout);
  const setLayout = useUiStore((s) => s.setLayout);
  const paneLayers = useUiStore((s) => s.paneLayers);
  const setPaneLayer = useUiStore((s) => s.setPaneLayer);
  const splitLayers = useUiStore((s) => s.splitLayers);
  const setSplitLayers = useUiStore((s) => s.setSplitLayers);

  const result = useParamsStore((s) => s.results[activeWorkspace]);
  const error = useParamsStore((s) => s.errors[activeWorkspace]);

  const currentFrame = useTimelineStore((s) => s.currentFrame);
  const currentFrameRef = result?.frames?.[currentFrame];

  const layers = result?.layers || [];
  const layerMap = React.useMemo(() => {
    const map = new Map<string, { url: string; width: number; height: number }>();
    layers.forEach((l) => map.set(l.name, { url: l.url, width: l.width, height: l.height }));

    // Merge frame layers if active in sequence
    if (currentFrameRef) {
      Object.entries(currentFrameRef.layers).forEach(([k, url]) => {
        const baseLayer = layers[0];
        map.set(k, {
          url,
          width: baseLayer?.width || 512,
          height: baseLayer?.height || 512,
        });
      });
    }
    return map;
  }, [layers, currentFrameRef]);

  // Empty / Error states map
  const renderEmptyState = () => {
    if (error) {
      const code = error.code || error.detail?.code || "bad_media";
      let text = "Unreadable File";
      if (code === "need_two_images") text = "2 Images Required";
      if (code === "need_two_frames") text = "2+ Frames Required";
      if (code === "need_three_frames") text = "3+ Frames Required";
      if (code === "no_video_backend") text = "No Video Decoder";
      if (code === "server_offline") text = "Server Offline";

      return (
        <div className={styles.emptyState}>
          <span className={styles.emptyStateText}>{text}</span>
          {code !== "no_video_backend" && (
            <Button size="sm" variant="default" onClick={onImportClick}>
              Import
            </Button>
          )}
        </div>
      );
    }

    if (!result) {
      return (
        <div className={styles.emptyState}>
          <span className={styles.emptyStateText}>Drop Images</span>
          <Button size="sm" variant="default" onClick={onImportClick}>
            Import
          </Button>
        </div>
      );
    }

    return null;
  };

  const getLayerData = (layerName: string) => {
    const found = layerMap.get(layerName);
    if (found) return found;
    const first = layers[0];
    if (first) return { url: first.url, width: first.width, height: first.height };
    return { url: undefined, width: 512, height: 512 };
  };

  const layerOptions = layers.map((l) => ({ value: l.name, label: l.name }));
  if (currentFrameRef) {
    Object.keys(currentFrameRef.layers).forEach((k) => {
      if (!layerOptions.some((o) => o.value === k)) {
        layerOptions.push({ value: k, label: k });
      }
    });
  }

  return (
    <div className={styles.viewerContainer}>
      {/* Document Tabs & Layout Switcher Bar */}
      <div className={styles.viewerHeader}>
        <div className={styles.documentTabs}>
          {layers.map((l) => {
            const isActive = paneLayers[0] === l.name;
            return (
              <button
                key={l.id}
                type="button"
                className={clsx(styles.docTab, isActive && styles.docTabActive)}
                onClick={() => setPaneLayer(0, l.name)}
              >
                {l.name}
              </button>
            );
          })}
        </div>

        <div className={styles.headerRightControls}>
          {layout === "split" && layerOptions.length >= 2 && (
            <div className={styles.splitSelects}>
              <Select
                options={layerOptions}
                value={splitLayers[0]}
                onChange={(v) => setSplitLayers([v, splitLayers[1]])}
              />
              <span className={styles.splitSep}>|</span>
              <Select
                options={layerOptions}
                value={splitLayers[1]}
                onChange={(v) => setSplitLayers([splitLayers[0], v])}
              />
            </div>
          )}

          <div className={styles.layoutSwitch}>
            <IconButton
              size="sm"
              icon={<Square size={13} />}
              active={layout === "1up"}
              onClick={() => setLayout("1up")}
              tooltip="1-Up (Ctrl+1)"
            />
            <IconButton
              size="sm"
              icon={<Columns size={13} />}
              active={layout === "2up"}
              onClick={() => setLayout("2up")}
              tooltip="2-Up"
            />
            <IconButton
              size="sm"
              icon={<LayoutGrid size={13} />}
              active={layout === "4up"}
              onClick={() => setLayout("4up")}
              tooltip="4-Up"
            />
            <IconButton
              size="sm"
              icon={<SplitSquareVertical size={13} />}
              active={layout === "split"}
              onClick={() => setLayout("split")}
              tooltip="Compare Split (C)"
            />
          </div>
        </div>
      </div>

      {/* Spectrum StageStrip if in Spectrum Workspace */}
      {activeWorkspace === "spectrum" && <StageStrip />}

      {/* Pasteboard & Canvas */}
      <div className={styles.pasteboard}>
        {renderEmptyState() || (
          <>
            {layout === "1up" && (
              <Pane
                layerName={paneLayers[0] || layers[0]?.name || "Output"}
                layerUrl={getLayerData(paneLayers[0] || layers[0]?.name).url}
                width={getLayerData(paneLayers[0] || layers[0]?.name).width}
                height={getLayerData(paneLayers[0] || layers[0]?.name).height}
                markers={result?.markers}
                onProbeClick={onProbeClick}
                className={styles.fullPane}
              />
            )}

            {layout === "2up" && (
              <div className={styles.twoUpGrid}>
                <Pane
                  layerName={paneLayers[0] || layers[0]?.name || "Left"}
                  layerUrl={getLayerData(paneLayers[0] || layers[0]?.name).url}
                  width={getLayerData(paneLayers[0] || layers[0]?.name).width}
                  height={getLayerData(paneLayers[0] || layers[0]?.name).height}
                  markers={result?.markers}
                  onProbeClick={onProbeClick}
                />
                <Pane
                  layerName={paneLayers[1] || layers[1]?.name || layers[0]?.name || "Right"}
                  layerUrl={getLayerData(paneLayers[1] || layers[1]?.name || layers[0]?.name).url}
                  width={getLayerData(paneLayers[1] || layers[1]?.name || layers[0]?.name).width}
                  height={getLayerData(paneLayers[1] || layers[1]?.name || layers[0]?.name).height}
                  markers={result?.markers}
                  onProbeClick={onProbeClick}
                />
              </div>
            )}

            {layout === "4up" && (
              <div className={styles.fourUpGrid}>
                {[0, 1, 2, 3].map((idx) => {
                  const lName = paneLayers[idx] || layers[idx]?.name || layers[0]?.name || `Layer ${idx + 1}`;
                  const lData = getLayerData(lName);
                  return (
                    <Pane
                      key={idx}
                      layerName={lName}
                      layerUrl={lData.url}
                      width={lData.width}
                      height={lData.height}
                      markers={result?.markers}
                      onProbeClick={onProbeClick}
                    />
                  );
                })}
              </div>
            )}

            {layout === "split" && (
              <SplitCompare
                layerLeftName={splitLayers[0]}
                layerRightName={splitLayers[1]}
                layerLeftUrl={getLayerData(splitLayers[0]).url}
                layerRightUrl={getLayerData(splitLayers[1]).url}
                width={getLayerData(splitLayers[0]).width}
                height={getLayerData(splitLayers[0]).height}
                onProbeClick={onProbeClick}
                className={styles.fullPane}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};
