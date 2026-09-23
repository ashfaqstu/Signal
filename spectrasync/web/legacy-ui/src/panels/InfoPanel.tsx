import React from "react";
import clsx from "clsx";
import styles from "./Panels.module.css";
import { Panel } from "./Panel";
import { useUiStore } from "../state/ui";
import { useParamsStore } from "../state/params";
import { useTimelineStore } from "../state/timeline";
import { formatReadout } from "../lib/format";
import { VerdictChip } from "../controls/VerdictChip";
import { Badge } from "../controls/Badge";

export const InfoPanel: React.FC = () => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const result = useParamsStore((s) => s.results[activeWorkspace]);
  const error = useParamsStore((s) => s.errors[activeWorkspace]);
  const currentFrame = useTimelineStore((s) => s.currentFrame);

  // Read frame-level metadata if in sequence workspace
  const currentFrameRef = result?.frames?.[currentFrame];
  const frameMeta = currentFrameRef?.meta || {};

  const flagMap: Record<string, string> = {
    inverted_contrast: "Inverted",
  };

  return (
    <Panel title="Info" className={styles.infoPanel}>
      {result ? (
        <div className={styles.infoContainer}>
          {result.verdict && (
            <div className={styles.infoVerdictRow}>
              <span className={styles.readoutLabel}>Status</span>
              <VerdictChip verdict={result.verdict} />
            </div>
          )}

          {result.flags.length > 0 && (
            <div className={styles.infoFlagsRow}>
              {result.flags.map((fl) => (
                <Badge
                  key={fl}
                  label={flagMap[fl] || fl}
                  tone="warn"
                />
              ))}
            </div>
          )}

          <div className={styles.readoutList}>
            {result.readouts.map((r) => (
              <div key={r.key} className={styles.readoutRow}>
                <span className={styles.readoutLabel}>{r.label}</span>
                <span className={clsx(styles.readoutValue, "tabular-nums", styles[`tone-${r.tone || "default"}`])}>
                  {formatReadout(r.value, r.fmt, r.unit)}
                </span>
              </div>
            ))}

            {/* Frame specific readouts in Highlight workspace */}
            {activeWorkspace === "highlight" && currentFrameRef && (
              <>
                <div className={styles.readoutDivider} />
                <div className={styles.readoutRow}>
                  <span className={styles.readoutLabel}>Frame</span>
                  <span className={clsx(styles.readoutValue, "tabular-nums")}>
                    #{currentFrame + 1}
                  </span>
                </div>
                {frameMeta.objects !== undefined && (
                  <div className={styles.readoutRow}>
                    <span className={styles.readoutLabel}>Objects</span>
                    <span className={clsx(styles.readoutValue, "tabular-nums")}>
                      {frameMeta.objects}
                    </span>
                  </div>
                )}
                {frameMeta.largest && (
                  <div className={styles.readoutRow}>
                    <span className={styles.readoutLabel}>Largest</span>
                    <span className={clsx(styles.readoutValue, "tabular-nums")}>
                      ({frameMeta.largest})
                    </span>
                  </div>
                )}
                {frameMeta.size && (
                  <div className={styles.readoutRow}>
                    <span className={styles.readoutLabel}>Size</span>
                    <span className={clsx(styles.readoutValue, "tabular-nums")}>
                      {frameMeta.size}
                    </span>
                  </div>
                )}
                {frameMeta.threshold !== undefined && (
                  <div className={styles.readoutRow}>
                    <span className={styles.readoutLabel}>Threshold</span>
                    <span className={clsx(styles.readoutValue, "tabular-nums")}>
                      {formatReadout(frameMeta.threshold, ".4f")}
                    </span>
                  </div>
                )}
                {frameMeta.coverage !== undefined && (
                  <div className={styles.readoutRow}>
                    <span className={styles.readoutLabel}>Coverage</span>
                    <span className={clsx(styles.readoutValue, "tabular-nums")}>
                      {formatReadout(frameMeta.coverage, ".2f", "%")}
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      ) : error ? (
        <div className={styles.infoEmpty}>
          <span className={styles.errorText}>No Analysis</span>
        </div>
      ) : (
        <div className={styles.infoEmpty}>
          <span>Ready</span>
        </div>
      )}
    </Panel>
  );
};
