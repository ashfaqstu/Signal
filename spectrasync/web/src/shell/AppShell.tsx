import { Clock3, FolderOpen, Home, Monitor, Moon, Plus, Sun, Waves } from "lucide-react";
import type { ReactNode } from "react";
import { useHealth, useMedia } from "../api/queries";
import { go, type Route } from "../lib/router";
import { useStudio, type ThemeMode } from "../state/studio";
import { TOOLS } from "../tools/catalog";
import { Button, Menu, MenuItem, Segmented, ToolBadge, cx } from "../ui";
import s from "./Shell.module.css";

export function Logo() {
  return (
    <span className={s.logo}>
      <Waves size={19} strokeWidth={2.4} />
    </span>
  );
}

export function ThemeSwitch() {
  const theme = useStudio((st) => st.theme);
  const setTheme = useStudio((st) => st.setTheme);
  return (
    <Segmented<ThemeMode>
      ariaLabel="Theme"
      value={theme}
      onChange={setTheme}
      options={[
        { value: "light", label: "", icon: Sun },
        { value: "system", label: "", icon: Monitor },
        { value: "dark", label: "", icon: Moon },
      ]}
    />
  );
}

export function CreateMenu({ variant = "primary" }: { variant?: "primary" | "white" }) {
  return (
    <Menu
      trigger={(_, toggle) => (
        <Button variant={variant} icon={Plus} onClick={toggle} className={s.create}>
          Create
        </Button>
      )}
    >
      {(close) =>
        TOOLS.map((t) => (
          <MenuItem
            key={t.id}
            icon={<ToolBadge icon={t.icon} gradient={t.gradient} size={32} radius={9} />}
            label={t.name}
            sub={t.tagline}
            onClick={() => {
              close();
              go(`/tool/${t.id}`);
            }}
          />
        ))
      }
    </Menu>
  );
}

export function AppShell({ route, children }: { route: Route; children: ReactNode }) {
  const health = useHealth();
  const media = useMedia().data ?? [];
  const history = useStudio((st) => st.history);
  const nav = [
    { page: "home", label: "Home", icon: Home, href: "/" },
    { page: "media", label: "Media", icon: FolderOpen, href: "/media", count: media.length },
    { page: "history", label: "History", icon: Clock3, href: "/history", count: history.length },
  ];

  return (
    <div className={s.shell}>
      <aside className={s.sidebar}>
        <a className={s.brand} href="#/">
          <Logo />
          SpectraSync
        </a>
        <CreateMenu />
        <nav className={s.nav}>
          {nav.map((n) => (
            <a key={n.page} href={`#${n.href}`} className={cx(s.navItem, route.page === n.page && s.navOn)}>
              <n.icon size={18} strokeWidth={2} />
              {n.label}
              {n.count ? <span className={s.navCount}>{n.count}</span> : null}
            </a>
          ))}
        </nav>

        <span className={s.section}>Tools</span>
        <div className={s.toolLinks}>
          {TOOLS.map((t) => (
            <a key={t.id} href={`#/tool/${t.id}`} className={s.toolLink}>
              <ToolBadge icon={t.icon} gradient={t.gradient} size={26} radius={7} />
              {t.name}
            </a>
          ))}
        </div>

        <div className={s.foot}>
          <ThemeSwitch />
          <div className={s.server}>
            <span className={cx(s.serverDot, health.isError && s.serverDown)} />
            {health.isError ? "Server offline" : health.data ? `Engine v${health.data.version}` : "Connecting"}
          </div>
        </div>
      </aside>
      <main className={s.main}>
        <div className={s.page} key={route.page}>
          {children}
        </div>
      </main>
    </div>
  );
}
