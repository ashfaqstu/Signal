import React, { useEffect } from "react";
import { Hand, ZoomIn, Pipette, SplitSquareVertical } from "lucide-react";
import styles from "./Shell.module.css";
import { useUiStore } from "../state/ui";
import { IconButton } from "../controls/IconButton";

export const ToolBar: React.FC = () => {
  const activeTool = useUiStore((s) => s.activeTool);
  const setActiveTool = useUiStore((s) => s.setActiveTool);
  const setLayout = useUiStore((s) => s.setLayout);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
        return;
      }

      if (e.key === "h" || e.key === "H") {
        setActiveTool("hand");
      } else if (e.key === "z" || e.key === "Z") {
        setActiveTool("zoom");
      } else if (e.key === "i" || e.key === "I") {
        setActiveTool("probe");
      } else if (e.key === "c" || e.key === "C") {
        setActiveTool("split");
        setLayout("split");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setActiveTool, setLayout]);

  return (
    <div className={styles.toolbar}>
      <IconButton
        size="tool"
        icon={<Hand size={16} />}
        active={activeTool === "hand"}
        onClick={() => setActiveTool("hand")}
        tooltip="Hand Tool (H / Space+Drag)"
      />
      <IconButton
        size="tool"
        icon={<ZoomIn size={16} />}
        active={activeTool === "zoom"}
        onClick={() => setActiveTool("zoom")}
        tooltip="Zoom Tool (Z / Alt+Click)"
      />
      <IconButton
        size="tool"
        icon={<Pipette size={16} />}
        active={activeTool === "probe"}
        onClick={() => setActiveTool("probe")}
        tooltip="Probe Tool (I)"
      />
      <IconButton
        size="tool"
        icon={<SplitSquareVertical size={16} />}
        active={activeTool === "split"}
        onClick={() => {
          setActiveTool("split");
          setLayout("split");
        }}
        tooltip="Compare Split Tool (C)"
      />
    </div>
  );
};
