import React from "react";
import { Play, Loader2 } from "lucide-react";
import styles from "./Panels.module.css";
import { Panel } from "./Panel";
import { getWorkspaceDef } from "../workspaces";
import { useParamsStore } from "../state/params";
import { useUiStore } from "../state/ui";
import { useRegistries } from "../api/queries";
import { ScrubField } from "../controls/ScrubField";
import { Select } from "../controls/Select";
import { Checkbox } from "../controls/Checkbox";
import { Segmented } from "../controls/Segmented";
import { MediaSlot } from "../controls/MediaSlot";
import { MediaMultiSlot } from "../controls/MediaMultiSlot";
import { Button } from "../controls/Button";

export interface PropertiesPanelProps {
  onRun?: () => void;
}

export const PropertiesPanel: React.FC<PropertiesPanelProps> = ({ onRun }) => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const preview = useUiStore((s) => s.preview);
  const setPreview = useUiStore((s) => s.setPreview);
  const running = useUiStore((s) => s.running);

  const params = useParamsStore((s) => (s.params as any)[activeWorkspace] || {});
  const setParam = useParamsStore((s) => s.setParam);

  const { data: registries } = useRegistries();
  const def = getWorkspaceDef(activeWorkspace);

  const renderParam = (p: any) => {
    if (p.when && !p.when(params)) return null;

    const val = params[p.key] !== undefined ? params[p.key] : p.default;

    if (p.type === "number") {
      return (
        <ScrubField
          key={p.key}
          label={p.label}
          value={Number(val)}
          defaultValue={p.default}
          min={p.min}
          max={p.max}
          step={p.step}
          unit={p.unit}
          decimals={p.decimals}
          onChange={(v) => setParam(activeWorkspace as any, p.key, v)}
        />
      );
    }

    if (p.type === "choice") {
      if (p.display === "segmented") {
        return (
          <div key={p.key} className={styles.paramRowBlock}>
            <span className={styles.rowLabel}>{p.label}</span>
            <Segmented
              options={p.options}
              value={String(val)}
              onChange={(v) => setParam(activeWorkspace as any, p.key, v)}
            />
          </div>
        );
      }
      return (
        <Select
          key={p.key}
          label={p.label}
          options={p.options}
          value={String(val)}
          onChange={(v) => setParam(activeWorkspace as any, p.key, v)}
        />
      );
    }

    if (p.type === "registry") {
      const regItems = registries ? (registries as any)[p.registry] || [] : [];
      const options = regItems.map((item: any) => ({
        value: item.name,
        label: item.name,
      }));
      return (
        <Select
          key={p.key}
          label={p.label}
          options={options.length > 0 ? options : [{ value: p.default, label: p.default }]}
          value={String(val || p.default)}
          onChange={(v) => setParam(activeWorkspace as any, p.key, v)}
        />
      );
    }

    if (p.type === "toggle") {
      return (
        <div key={p.key} className={styles.toggleRow}>
          <Checkbox
            label={p.label}
            checked={Boolean(val)}
            onChange={(checked) => setParam(activeWorkspace as any, p.key, checked)}
          />
        </div>
      );
    }

    if (p.type === "media") {
      return (
        <MediaSlot
          key={p.key}
          label={p.label}
          value={String(val || "")}
          accept={p.accept}
          onChange={(id) => setParam(activeWorkspace as any, p.key, id)}
        />
      );
    }

    if (p.type === "mediaMany") {
      return (
        <MediaMultiSlot
          key={p.key}
          label={p.label}
          value={Array.isArray(val) ? val : []}
          onChange={(ids) => setParam(activeWorkspace as any, p.key, ids)}
        />
      );
    }

    return null;
  };

  return (
    <Panel title="Properties" collapsible={false} className={styles.propertiesPanel}>
      <div className={styles.paramGroups}>
        {def.groups.map((group) => {
          const visibleParams = group.params.filter((p) => !p.when || p.when(params));
          if (visibleParams.length === 0) return null;
          return (
            <div key={group.title} className={styles.paramGroup}>
              <div className={styles.paramGroupTitle}>{group.title}</div>
              <div className={styles.paramGroupItems}>
                {group.params.map((p) => renderParam(p))}
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.propertiesFooter}>
        <Checkbox
          label="Preview"
          checked={preview}
          onChange={setPreview}
        />
        <Button
          variant="primary"
          icon={running ? <Loader2 size={14} className={styles.spinner} /> : <Play size={14} />}
          onClick={onRun}
          disabled={running}
        >
          Run
        </Button>
      </div>
    </Panel>
  );
};
