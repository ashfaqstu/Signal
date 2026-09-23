import { useEffect, useState } from "react";

/** Tiny hash router: #/  #/media  #/history  #/tool/<id> */
export type Route =
  | { page: "home" }
  | { page: "media" }
  | { page: "history" }
  | { page: "tool"; id: string };

function parse(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "tool" && parts[1]) return { page: "tool", id: parts[1] };
  if (parts[0] === "media") return { page: "media" };
  if (parts[0] === "history") return { page: "history" };
  return { page: "home" };
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function go(path: string) {
  window.location.hash = path;
}
