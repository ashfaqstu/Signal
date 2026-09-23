import React, { useRef } from "react";
import clsx from "clsx";
import { Upload, Trash2, Folder, Film, Image as ImageIcon } from "lucide-react";
import styles from "./Panels.module.css";
import { useMedia, useImportMedia, useDeleteMedia } from "../api/queries";
import { MediaItem } from "../api/types";
import { Button } from "../controls/Button";

export interface MediaPanelProps {
  onImportClick?: () => void;
}

export const MediaPanel: React.FC<MediaPanelProps> = ({ onImportClick }) => {
  const { data: mediaItems = [] } = useMedia();
  const importMutation = useImportMedia();
  const deleteMutation = useDeleteMedia();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      importMutation.mutate(Array.from(e.target.files));
    }
  };

  const grouped = mediaItems.reduce<Record<string, MediaItem[]>>((acc, item) => {
    acc[item.group] = acc[item.group] || [];
    acc[item.group].push(item);
    return acc;
  }, {});

  return (
    <div className={styles.mediaPanelContent}>
      <div className={styles.mediaPanelToolbar}>
        <input
          type="file"
          ref={fileInputRef}
          multiple
          accept="image/*,video/*"
          style={{ display: "none" }}
          onChange={handleFileUpload}
        />
        <Button
          size="sm"
          variant="default"
          icon={<Upload size={12} />}
          onClick={() => (onImportClick ? onImportClick() : fileInputRef.current?.click())}
          disabled={importMutation.isPending}
        >
          {importMutation.isPending ? "Importing…" : "Import"}
        </Button>
      </div>

      <div className={styles.mediaGroupList}>
        {Object.entries(grouped).map(([groupName, items]) => (
          <div key={groupName} className={styles.mediaBinGroup}>
            <div className={styles.mediaBinGroupHeader}>
              <Folder size={12} />
              <span>{groupName}</span>
              <span className={clsx(styles.binGroupCount, "tabular-nums")}>
                ({items.length})
              </span>
            </div>
            <div className={styles.mediaBinGrid}>
              {items.map((item) => (
                <div key={item.id} className={styles.mediaBinCard}>
                  <div className={styles.mediaCardThumbWrap}>
                    <img
                      src={`/api/media/${item.id}/thumb.jpg`}
                      alt={item.name}
                      className={styles.mediaCardThumb}
                    />
                    <div className={styles.mediaKindBadge}>
                      {item.kind === "video" ? <Film size={10} /> : <ImageIcon size={10} />}
                    </div>
                    {!item.sample && (
                      <button
                        type="button"
                        className={styles.mediaDeleteBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteMutation.mutate(item.id);
                        }}
                        title="Delete"
                      >
                        <Trash2 size={10} />
                      </button>
                    )}
                  </div>
                  <span className={styles.mediaCardTitle} title={item.name}>
                    {item.name}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
