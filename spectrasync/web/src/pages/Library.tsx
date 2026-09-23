import { Clock3, Trash2 } from "lucide-react";
import { useState } from "react";
import { MediaGrid } from "../media/MediaGrid";
import { useStudio } from "../state/studio";
import { Button, Segmented } from "../ui";
import { startTool } from "./Home";
import s from "./Home.module.css";
import { Empty, HistoryCard } from "./parts";

export function MediaPage() {
  const [filter, setFilter] = useState<"all" | "uploads" | "samples">("all");
  return (
    <>
      <div className={s.pageHead}>
        <h1 className={s.h1}>Media</h1>
        <div style={{ width: 300 }}>
          <Segmented
            ariaLabel="Filter"
            value={filter}
            onChange={setFilter}
            options={[
              { value: "all", label: "All" },
              { value: "uploads", label: "Uploads" },
              { value: "samples", label: "Samples" },
            ]}
          />
        </div>
      </div>
      <MediaGrid filter={filter} />
    </>
  );
}

export function HistoryPage() {
  const history = useStudio((st) => st.history);
  const clear = useStudio((st) => st.clearHistory);
  return (
    <>
      <div className={s.pageHead}>
        <h1 className={s.h1}>History</h1>
        {history.length > 0 && (
          <Button variant="ghost" icon={Trash2} onClick={clear}>
            Clear
          </Button>
        )}
      </div>
      {history.length ? (
        <div className={s.cards}>
          {history.map((e, i) => (
            <HistoryCard key={e.id} e={e} i={i} />
          ))}
        </div>
      ) : (
        <Empty
          icon={<Clock3 size={26} />}
          title="No runs yet"
          action={
            <Button variant="primary" onClick={() => startTool("remove")}>
              Try a sample
            </Button>
          }
        />
      )}
    </>
  );
}
