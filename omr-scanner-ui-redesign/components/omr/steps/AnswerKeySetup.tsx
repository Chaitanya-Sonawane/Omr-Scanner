'use client';

import { useState } from 'react';
import { Upload, Check } from 'lucide-react';
import DragDropZone from '../DragDropZone';

type TabType = 'upload' | 'manual' | 'saved';

interface AnswerKeySetupProps {
  onKeySet: (key: { [key: number]: string }) => void;
  isDisabled?: boolean;
  isKeySet?: boolean;
}

export default function AnswerKeySetup({
  onKeySet,
  isDisabled = false,
  isKeySet = false,
}: AnswerKeySetupProps) {
  const [activeTab, setActiveTab] = useState<TabType>('upload');
  const [uploadedImage, setUploadedImage] = useState<File | null>(null);
  const [manualAnswers, setManualAnswers] = useState<{ [key: number]: string }>({});

  const handleFileSelect = (files: File[]) => {
    if (files.length > 0) {
      setUploadedImage(files[0]);
      // Simulate answer key extraction
      const simulatedKey = Object.fromEntries(
        Array.from({ length: 40 }, (_, i) => [
          i + 1,
          ['A', 'B', 'C', 'D'][Math.floor(Math.random() * 4)],
        ])
      );
      setManualAnswers(simulatedKey);
    }
  };

  const handleAnswerChange = (questionNum: number, value: string) => {
    setManualAnswers((prev) => ({
      ...prev,
      [questionNum]: value,
    }));
  };

  const handleConfirm = () => {
    if (Object.keys(manualAnswers).length === 40) {
      onKeySet(manualAnswers);
    }
  };

  if (isKeySet) {
    return (
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/20 text-accent">
            <Check className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-foreground">Answer Key Set</h3>
            <p className="text-sm text-muted-foreground mt-1">
              40 questions configured. Ready to upload student sheets.
            </p>
            <div className="mt-3 text-xs text-muted-foreground">
              Questions 1-40: {Object.keys(manualAnswers).length > 0 ? '✓ Complete' : 'Pending'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h2 className="text-xl font-bold text-foreground mb-6">Step 1: Set Answer Key</h2>

      {/* Tabs */}
      <div className="mb-6 flex gap-2 border-b border-border">
        {(['upload', 'manual', 'saved'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            disabled={isDisabled}
            className={`px-4 py-3 text-sm font-medium transition-all border-b-2 -mb-[2px] ${
              activeTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab === 'upload' && 'Upload Image'}
            {tab === 'manual' && 'Manual Entry'}
            {tab === 'saved' && 'Use Saved'}
          </button>
        ))}
      </div>

      {/* Upload Tab */}
      {activeTab === 'upload' && (
        <div className="space-y-4">
          <DragDropZone
            onFilesSelected={handleFileSelect}
            accept="image/*"
            multiple={false}
            label="Upload OMR Sheet Image"
            description="Drag and drop your answer key OMR sheet here"
            disabled={isDisabled}
            selectedFiles={uploadedImage ? [uploadedImage] : []}
            onRemoveFile={() => {
              setUploadedImage(null);
              setManualAnswers({});
            }}
          />
          {uploadedImage && Object.keys(manualAnswers).length === 40 && (
            <div className="rounded-lg bg-accent/10 p-4 border border-accent/20">
              <p className="text-sm text-accent font-medium">
                ✓ Answer key extracted successfully
              </p>
            </div>
          )}
        </div>
      )}

      {/* Manual Entry Tab */}
      {activeTab === 'manual' && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 40 }, (_, i) => i + 1).map((qNum) => (
              <div key={qNum} className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground">Q{qNum}</label>
                <div className="flex gap-2">
                  {['A', 'B', 'C', 'D'].map((opt) => (
                    <button
                      key={opt}
                      onClick={() => handleAnswerChange(qNum, opt)}
                      className={`flex-1 rounded py-2 text-sm font-medium transition-all ${
                        manualAnswers[qNum] === opt
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground hover:bg-border'
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Saved Tab */}
      {activeTab === 'saved' && (
        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <p className="text-sm text-muted-foreground text-center py-8">
            No previously saved answer keys found
          </p>
        </div>
      )}

      {/* Confirm Button */}
      {Object.keys(manualAnswers).length === 40 && (
        <div className="mt-6">
          <button
            onClick={handleConfirm}
            className="w-full rounded-lg bg-primary px-4 py-3 font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Confirm Answer Key
          </button>
        </div>
      )}
    </div>
  );
}
