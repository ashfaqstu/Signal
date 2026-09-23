import React from "react";
import katex from "katex";
import clsx from "clsx";
import { SPECTRUM_STAGES } from "./stages";
import styles from "./Spectrum.module.css";
import { useParamsStore } from "../../state/params";
import { useUiStore } from "../../state/ui";

export const StageStrip: React.FC = () => {
  const activeStage = useParamsStore((s) => s.params.spectrum.activeStage || 0);
  const setParam = useParamsStore((s) => s.setParam);
  const setPaneLayer = useUiStore((s) => s.setPaneLayer);

  const stage = SPECTRUM_STAGES[activeStage] || SPECTRUM_STAGES[0];

  const handleSelectStage = (idx: number) => {
    setParam("spectrum", "activeStage", idx);
    setPaneLayer(0, SPECTRUM_STAGES[idx].layer);
  };

  const renderedFormula = React.useMemo(() => {
    try {
      return katex.renderToString(stage.formula, {
        displayMode: false,
        throwOnError: false,
      });
    } catch {
      return stage.formula;
    }
  }, [stage.formula]);

  return (
    <div className={styles.stageStrip}>
      <div className={styles.stageTabs}>
        {SPECTRUM_STAGES.map((st) => (
          <button
            key={st.id}
            type="button"
            className={clsx(
              styles.stageTab,
              st.id === activeStage && styles.stageTabActive
            )}
            onClick={() => handleSelectStage(st.id)}
          >
            {st.title}
          </button>
        ))}
      </div>
      <div className={styles.formulaBar}>
        <div
          className={styles.formulaContent}
          dangerouslySetInnerHTML={{ __html: renderedFormula }}
        />
      </div>
    </div>
  );
};
