import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
import { getItem } from "./lib/storage";

import "./styles/tokens.css";
import "./styles/reset.css";
import "./styles/base.css";

// Initialize theme on root
const savedTheme = getItem<string>("spectrasync_theme", "system");
if (savedTheme && savedTheme !== "system") {
  document.documentElement.dataset.theme = savedTheme;
} else {
  delete document.documentElement.dataset.theme;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
