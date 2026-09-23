import React, { useState } from "react";
import clsx from "clsx";
import { Images, X } from "lucide-react";
import styles from "./Controls.module.css";
import { useMedia } from "../api/queries";
import { MediaItem } from "../api/types";

export interface MediaMultiSlotProps {
  label: string;
  value: string[];
  onChange: (mediaIds: string[]) => void;
  disabled?: boolean;
  className?: string;
}

export const MediaMultiSlot: React.FC<MediaMultiSlotProps> = ({
  label,
  value = [],
  onChange,
  disabled = false,
  className,
}) => {
  const [pickerOpen, setPickerOpen] = useState(false);
  const { data: mediaItems = [] } = useMedia();

  const selectedItems = value
    .map((id) => mediaItems.find((m) => m.id === id))
    .filter(Boolean) as MediaItem[];

  const imageItems = mediaItems.filter((m) => m.kind === "image");

  const grouped = imageItems.reduce<Record<string, MediaItem[]>>((acc, item) => {
    acc[item.group] = acc[item.group] || [];
    acc[item.group].push(item);
    return acc;
  }, {});

  const toggleItem = (id: string) => {
    if (value.includes(id)) {
      onChange(value.filter((x) => x !== id));
    } else {
      onChange([...value, id]);
    }
  };

  const selectGroup = (items: MediaItem[]) => {
    const ids = items.map((i) => i.id);
    const allSelected = ids.every((id) => value.includes(id));
    if (allSelected) {
      onChange(value.filter((id) => !ids.includes(id)));
    } else {
      const merged = Array.from(new Set([...value, ...ids]));
      onChange(merged);
    }
  };

  return (
    <div className={clsx(styles.mediaSlotContainer, className)}>
      <div className={styles.multiSlotHeader}>
        <span className={styles.fieldLabel}>{label}</span>
        <span className={clsx(styles.multiSlotCount, "tabular-nums")}>
          {value.length > 0 ? `${value.length} selected` : "default sample"}
        </span>
      </div>

      <div className={styles.mediaSlotWrapper}>
        <div
          className={clsx(styles.mediaMultiSlot, disabled && styles.disabled)}
          onClick={() => !disabled && setPickerOpen(!pickerOpen)}
        >
          {selectedItems.length > 0 ? (
            <div className={styles.multiSlotThumbs}>
              {selectedItems.slice(0, 5).map((item) => (
                <img
                  key={item.id}
                  src={`/api/media/${item.id}/thumb.jpg`}
                  alt={item.name}
                  className={styles.multiThumbItem}
                />
              ))}
              {selectedItems.length > 5 && (
                <span className={styles.multiThumbExtra}>+{selectedItems.length - 5}</span>
              )}
            </div>
          ) : (
            <div className={styles.mediaSlotEmpty}>
              <Images size={14} className={styles.mediaSlotIcon} />
              <span>Select photos (default active)</span>
            </div>
          )}

          {value.length > 0 && (
            <button
              type="button"
              className={styles.mediaSlotClear}
              onClick={(e) => {
                e.stopPropagation();
                onChange([]);
              }}
              title="Clear all"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {pickerOpen && (
          <div className={clsx(styles.mediaPickerPopover, "popover-card")}>
            <div className={styles.mediaPickerHeader}>
              <span>Pick photo frames ({value.length} selected)</span>
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
                  <div className={styles.mediaPickerGroupHeader}>
                    <span>{groupName}</span>
                    <button
                      type="button"
                      className={styles.groupSelectBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        selectGroup(items);
                      }}
                    >
                      {items.every((i) => value.includes(i.id)) ? "Deselect group" : "Select group"}
                    </button>
                  </div>
                  <div className={styles.mediaPickerGrid}>
                    {items.map((item) => {
                      const isSelected = value.includes(item.id);
                      return (
                        <div
                          key={item.id}
                          className={clsx(
                            styles.mediaPickerItem,
                            isSelected && styles.mediaPickerItemSelected
                          )}
                          onClick={() => toggleItem(item.id)}
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
                      );
                    })}
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
