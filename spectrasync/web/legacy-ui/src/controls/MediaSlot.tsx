import React, { useState, useRef } from "react";
import clsx from "clsx";
import { Image as ImageIcon, X } from "lucide-react";
import styles from "./Controls.module.css";
import { useMedia } from "../api/queries";
import { MediaItem } from "../api/types";

export interface MediaSlotProps {
  label: string;
  value: string;
  onChange: (mediaId: string) => void;
  accept?: "image" | "video";
  disabled?: boolean;
  className?: string;
}

export const MediaSlot: React.FC<MediaSlotProps> = ({
  label,
  value,
  onChange,
  accept = "image",
  disabled = false,
  className,
}) => {
  const [pickerOpen, setPickerOpen] = useState(false);
  const { data: mediaItems = [] } = useMedia();
  const pickerRef = useRef<HTMLDivElement>(null);

  const selectedMedia = mediaItems.find((m) => m.id === value);
  const filteredItems = mediaItems.filter((m) => m.kind === accept);

  // Group media by group label
  const grouped = filteredItems.reduce<Record<string, MediaItem[]>>((acc, item) => {
    acc[item.group] = acc[item.group] || [];
    acc[item.group].push(item);
    return acc;
  }, {});

  return (
    <div className={clsx(styles.mediaSlotContainer, className)}>
      <span className={styles.fieldLabel}>{label}</span>
      <div className={styles.mediaSlotWrapper}>
        <div
          className={clsx(
            styles.mediaSlot,
            selectedMedia && styles.mediaSlotFilled,
            disabled && styles.disabled
          )}
          onClick={() => !disabled && setPickerOpen(!pickerOpen)}
        >
          {selectedMedia ? (
            <>
              <img
                src={`/api/media/${selectedMedia.id}/thumb.jpg`}
                alt={selectedMedia.name}
                className={styles.mediaSlotThumb}
              />
              <span className={styles.mediaSlotName} title={selectedMedia.name}>
                {selectedMedia.name}
              </span>
              <button
                type="button"
                className={styles.mediaSlotClear}
                onClick={(e) => {
                  e.stopPropagation();
                  onChange("");
                }}
                title="Clear"
              >
                <X size={12} />
              </button>
            </>
          ) : (
            <div className={styles.mediaSlotEmpty}>
              <ImageIcon size={14} className={styles.mediaSlotIcon} />
              <span>Select {accept}</span>
            </div>
          )}
        </div>

        {pickerOpen && (
          <div className={clsx(styles.mediaPickerPopover, "popover-card")} ref={pickerRef}>
            <div className={styles.mediaPickerHeader}>
              <span>Pick {accept}</span>
              <button
                type="button"
                onClick={() => setPickerOpen(false)}
                className={styles.mediaPickerClose}
              >
                <X size={14} />
              </button>
            </div>
            <div className={styles.mediaPickerList}>
              {Object.entries(grouped).map(([groupName, items]) => (
                <div key={groupName} className={styles.mediaPickerGroup}>
                  <div className={styles.mediaPickerGroupHeader}>{groupName}</div>
                  <div className={styles.mediaPickerGrid}>
                    {items.map((item) => (
                      <div
                        key={item.id}
                        className={clsx(
                          styles.mediaPickerItem,
                          item.id === value && styles.mediaPickerItemSelected
                        )}
                        onClick={() => {
                          onChange(item.id);
                          setPickerOpen(false);
                        }}
                      >
                        <img
                          src={`/api/media/${item.id}/thumb.jpg`}
                          alt={item.name}
                          className={styles.mediaPickerItemThumb}
                        />
                        <span className={styles.mediaPickerItemName} title={item.name}>
                          {item.name}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
