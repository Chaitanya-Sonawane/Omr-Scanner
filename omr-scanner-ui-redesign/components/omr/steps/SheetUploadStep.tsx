'use client';

import { useState } from 'react';
import { Upload } from 'lucide-react';
import DragDropZone from '../DragDropZone';

interface SheetUploadStepProps {
  onSheetsSelected: (
    files: File[],
    studentInfo?: { [filename: string]: string }
  ) => void;
  isDisabled?: boolean;
  isKeySet?: boolean;
}

export default function SheetUploadStep({
  onSheetsSelected,
  isDisabled,
  isKeySet = false,
}: SheetUploadStepProps) {
  const disabled = isDisabled ?? !isKeySet;
  const [selectedSheets, setSelectedSheets] = useState<File[]>([]);
  const [studentNames, setStudentNames] = useState<{ [key: string]: string }>({});

  const handleFilesSelected = (files: File[]) => {
    setSelectedSheets((prev) => [...prev, ...files]);
  };

  const handleRemoveSheet = (index: number) => {
    setSelectedSheets((prev) => prev.filter((_, i) => i !== index));
  };

  const handleNameChange = (filename: string, name: string) => {
    setStudentNames((prev) => ({
      ...prev,
      [filename]: name,
    }));
  };

  const handleUpload = () => {
    onSheetsSelected(selectedSheets, studentNames);
  };

  if (!isKeySet) {
    return (
      <div className="rounded-xl border border-border bg-card/50 p-6 opacity-50">
        <h2 className="text-xl font-bold text-foreground mb-4">Step 2: Upload Student Sheets</h2>
        <p className="text-sm text-muted-foreground">
          Complete Step 1 (Set Answer Key) to enable sheet upload
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h2 className="text-xl font-bold text-foreground mb-6">Step 2: Upload Student Sheets</h2>

      <div className="space-y-6">
        <DragDropZone
          onFilesSelected={handleFilesSelected}
          accept="image/*"
          multiple={true}
          label="Drag & Drop Student Answer Sheets"
          description="Upload multiple OMR sheets for batch processing"
          disabled={disabled}
          selectedFiles={selectedSheets}
          onRemoveFile={handleRemoveSheet}
        />

        {selectedSheets.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-foreground">
                Student Information (Optional)
              </label>
              <span className="text-xs text-muted-foreground">
                {Object.keys(studentNames).length} / {selectedSheets.length} filled
              </span>
            </div>

            <div className="space-y-3 max-h-60 overflow-y-auto">
              {selectedSheets.map((file, idx) => (
                <div key={`${file.name}-${idx}`} className="flex gap-3 items-end">
                  <div className="flex-1 space-y-1">
                    <label className="block text-xs font-medium text-muted-foreground">
                      {file.name}
                    </label>
                    <input
                      type="text"
                      placeholder="Student Name/ID (optional)"
                      value={studentNames[file.name] || ''}
                      onChange={(e) => handleNameChange(file.name, e.target.value)}
                      className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {selectedSheets.length > 0 && (
          <div className="pt-4 border-t border-border">
            <button
              onClick={handleUpload}
              className="w-full rounded-lg bg-primary px-4 py-3 font-semibold text-primary-foreground hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
            >
              <Upload className="h-5 w-5" />
              Process {selectedSheets.length} Sheet{selectedSheets.length !== 1 ? 's' : ''}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
