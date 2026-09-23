import React from "react";
import clsx from "clsx";
import { Eye, EyeOff, Layers as LayersIcon } from "lucide-react";
import styles from "./Panels.module.css";
import { useUiStore } from "../state/ui";
import { useParamsStore } from "../state/params";
import { LayerRef } from "../api/types";

export const LayersPanel: React.FC = () => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const paneLayers = useUiStore((s) => s.paneLayers);
  const setPaneLayer = useUiStore((s) => s.setPaneLayer);
  const result = useParamsStore((s) => s.results[activeWorkspace]);

  const layers = result?.layers || [];

  const grouped = layers.reduce<Record<string, LayerRef[]>>((acc, l) => {
    acc[l.group] = acc[l.group] || [];
    acc[l.group].push(l);
    return acc;
  }, {});

  const handleSelectLayer = (layerName: string) => {
    setPaneLayer(0, layerName);
  };

  return (
    <div className={styles.layersPanelContent}>
      {layers.length > 0 ? (
        <div className={styles.layersList}>
          {Object.entries(grouped).map(([groupName, groupLayers]) => (
            <div key={groupName} className={styles.layerGroup}>
              <div className={styles.layerGroupHeader}>{groupName}</div>
              {groupLayers.map((l) => {
                const isActiveInPane = paneLayers.includes(l.name);
                return (
                  <div
                    key={l.id}
                    className={clsx(
                      styles.layerRow,
                      isActiveInPane && styles.layerRowActive
                    )}
                    onClick={() => handleSelectLayer(l.name)}
                  >
                    <span className={styles.layerVisibility}>
                      {isActiveInPane ? <Eye size={13} /> : <EyeOff size={13} className={styles.eyeOff} />}
                    </span>
                    <img
                      src={l.url}
                      alt={l.name}
                      className={styles.layerThumb}
                    />
                    <span className={styles.layerName}>{l.name}</span>
                    <span className={clsx(styles.layerDim, "tabular-nums")}>
                      {l.width}×{l.height}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      ) : (
        <div className={styles.emptyNotice}>
          <LayersIcon size={20} className={styles.emptyIcon} />
          <span>No Layers</span>
        </div>
      )}
    </div>
  );
};
