import { Editor } from "./editor/Editor";
import { useRoute } from "./lib/router";
import { Home } from "./pages/Home";
import { HistoryPage, MediaPage } from "./pages/Library";
import { AppShell } from "./shell/AppShell";
import { TOOL_BY_ID, isToolId } from "./tools/catalog";

export function App() {
  const route = useRoute();

  if (route.page === "tool" && isToolId(route.id)) {
    return <Editor key={route.id} tool={TOOL_BY_ID[route.id]} />;
  }

  return (
    <AppShell route={route}>
      {route.page === "media" ? <MediaPage /> : route.page === "history" ? <HistoryPage /> : <Home />}
    </AppShell>
  );
}
