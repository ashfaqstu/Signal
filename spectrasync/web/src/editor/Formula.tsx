import katex from "katex";
import "katex/dist/katex.min.css";

/** Loaded lazily: only the Spectrum tool shows formulas, so KaTeX stays out of the main bundle. */
export default function Formula({ tex, className }: { tex: string; className: string }) {
  return (
    <div className={className} dangerouslySetInnerHTML={{ __html: katex.renderToString(tex, { throwOnError: false }) }} />
  );
}
