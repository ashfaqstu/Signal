import React, { useState, useEffect } from "react";
import { Upload } from "lucide-react";
import styles from "./Shell.module.css";
import { useImportMedia } from "../api/queries";

export const DropOverlay: React.FC = () => {
  const [isDragOver, setIsDragOver] = useState(false);
  const importMutation = useImportMedia();

  useEffect(() => {
    let dragCounter = 0;

    const handleDragEnter = (e: DragEvent) => {
      e.preventDefault();
      dragCounter++;
      if (e.dataTransfer?.types.includes("Files")) {
        setIsDragOver(true);
      }
    };

    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      dragCounter--;
      if (dragCounter === 0) {
        setIsDragOver(false);
      }
    };

    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
    };

    const handleDrop = (e: DragEvent) => {
      e.preventDefault();
      dragCounter = 0;
      setIsDragOver(false);
      if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
        importMutation.mutate(Array.from(e.dataTransfer.files));
      }
    };

    window.addEventListener("dragenter", handleDragEnter);
    window.addEventListener("dragleave", handleDragLeave);
    window.addEventListener("dragover", handleDragOver);
    window.addEventListener("drop", handleDrop);

    return () => {
      window.removeEventListener("dragenter", handleDragEnter);
      window.removeEventListener("dragleave", handleDragLeave);
      window.removeEventListener("dragover", handleDragOver);
      window.removeEventListener("drop", handleDrop);
    };
  }, [importMutation]);

  if (!isDragOver) return null;

  return (
    <div className={styles.dropOverlay}>
      <div className={styles.dropBox}>
        <Upload size={32} className={styles.dropIcon} />
        <span className={styles.dropText}>Drop Files to Import</span>
      </div>
    </div>
  );
};
