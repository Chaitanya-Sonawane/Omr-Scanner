'use client';

import { Upload, X } from 'lucide-react';
import { useRef, useState } from 'react';

interface DragDropZoneProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  label?: string;
  description?: string;
  disabled?: boolean;
  selectedFiles?: File[];
  onRemoveFile?: (index: number) => void;
}

export default function DragDropZone({
  onFilesSelected,
  accept = 'image/*',
  multiple = true,
  label = 'Upload Files',
  description = 'Drag and drop or click to select',
  disabled = false,
  selectedFiles = [],
  onRemoveFile,
}: DragDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (!disabled) {
      const files = Array.from(e.dataTransfer.files);
      onFilesSelected(files);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onFilesSelected(Array.from(e.target.files));
    }
  };

  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`relative rounded-xl border-2 border-dashed transition-all duration-300 cursor-pointer transform ${
          disabled
            ? 'border-border bg-muted opacity-50 cursor-not-allowed'
            : isDragging
              ? 'border-primary bg-primary/5 scale-[1.02]'
              : 'border-border hover:border-primary hover:bg-card/50 hover:scale-[1.01]'
        }`}
      >
        <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 sm:py-16">
          <div
            className={`rounded-full p-3 transition-all duration-300 ${
              isDragging 
                ? 'bg-primary/10 scale-110 animate-pulse' 
                : 'bg-muted group-hover:bg-primary/5'
            }`}
          >
            <Upload 
              className={`h-6 w-6 transition-colors ${
                isDragging ? 'text-primary' : 'text-muted-foreground'
              }`} 
            />
          </div>
          <div className="text-center">
            <p className="font-semibold text-foreground">{label}</p>
            <p className="text-sm text-muted-foreground">{description}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Supports: JPG, PNG, PDF
            </p>
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleInputChange}
          className="hidden"
          disabled={disabled}
        />
      </div>

      {selectedFiles.length > 0 && (
        <div className="mt-4 space-y-2 animate-in fade-in duration-300">
          <p className="text-xs font-medium text-muted-foreground">
            {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
          </p>
          <ul className="space-y-2">
            {selectedFiles.map((file, idx) => (
              <li
                key={`${file.name}-${idx}`}
                className="flex items-center justify-between gap-3 rounded-lg bg-card border border-border px-3 py-2 animate-in slide-in-from-left duration-300 hover:border-primary transition-all"
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <span className="flex-1 truncate text-sm text-foreground">
                  {file.name}
                </span>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
                {onRemoveFile && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveFile(idx);
                    }}
                    className="text-muted-foreground hover:text-destructive transition-colors hover:scale-110"
                    aria-label="Remove file"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
