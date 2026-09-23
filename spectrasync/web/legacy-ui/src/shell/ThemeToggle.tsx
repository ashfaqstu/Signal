import React from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { useUiStore } from "../state/ui";
import { IconButton } from "../controls/IconButton";

export const ThemeToggle: React.FC = () => {
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);

  const getIcon = () => {
    if (theme === "light") return <Sun size={14} />;
    if (theme === "dark") return <Moon size={14} />;
    return <Monitor size={14} />;
  };

  const getTooltip = () => {
    if (theme === "light") return "Theme: Light (Click for Dark)";
    if (theme === "dark") return "Theme: Dark (Click for System)";
    return "Theme: System (Click for Light)";
  };

  return (
    <IconButton
      size="sm"
      icon={getIcon()}
      onClick={toggleTheme}
      tooltip={getTooltip()}
    />
  );
};
