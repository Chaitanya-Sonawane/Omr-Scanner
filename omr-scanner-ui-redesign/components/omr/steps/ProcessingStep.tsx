'use client';

import { useEffect, useState } from 'react';
import StatusBadge from '../StatusBadge';

interface ProcessingItem {
  id: string;
  filename: string;
  studentId?: string;
  status: 'queued' | 'processing' | 'done' | 'error';
  score?: number;
  progress?: number;
}

interface ProcessingStepProps {
  items?: ProcessingItem[];
  isProcessing?: boolean;
  isVisible?: boolean;
}

export default function ProcessingStep({
  items = [],
  isProcessing = false,
  isVisible = false,
}: ProcessingStepProps) {
  const [displayItems, setDisplayItems] = useState<ProcessingItem[]>(items);

  useEffect(() => {
    setDisplayItems(items);
  }, [items]);

  if (!isVisible || displayItems.length === 0) {
    return null;
  }

  const stats = {
    total: displayItems.length,
    completed: displayItems.filter((i) => i.status === 'done').length,
    processing: displayItems.filter((i) => i.status === 'processing').length,
    errors: displayItems.filter((i) => i.status === 'error').length,
  };

  const completionPercentage = Math.round(
    ((stats.completed + stats.errors) / stats.total) * 100
  );

  return (
    <div className="rounded-xl border border-border bg-card p-4 sm:p-6">
      <h2 className="text-lg sm:text-xl font-bold text-foreground mb-4 sm:mb-6">Step 3: Live Processing</h2>

      {/* Progress Overview */}
      <div className="mb-6 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs sm:text-sm font-semibold text-foreground">Processing Progress</span>
          <span className="text-xs sm:text-sm font-bold text-primary whitespace-nowrap">
            {stats.completed + stats.errors}/{stats.total}
          </span>
        </div>

        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-accent transition-all duration-300"
            style={{ width: `${completionPercentage}%` }}
          />
        </div>

        {/* Stats Grid - Responsive */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 text-xs">
          <div className="rounded bg-muted/50 px-2 sm:px-3 py-2 text-center">
            <p className="font-bold text-foreground text-sm sm:text-base">{stats.total}</p>
            <p className="text-muted-foreground text-xs">Total</p>
          </div>
          <div className="rounded bg-blue-100 dark:bg-blue-900/30 px-2 sm:px-3 py-2 text-center">
            <p className="font-bold text-blue-700 dark:text-blue-300 text-sm sm:text-base">{stats.processing}</p>
            <p className="text-blue-600 dark:text-blue-400 text-xs">Processing</p>
          </div>
          <div className="rounded bg-accent/10 px-2 sm:px-3 py-2 text-center">
            <p className="font-bold text-accent text-sm sm:text-base">{stats.completed}</p>
            <p className="text-accent/70 text-xs">Done</p>
          </div>
          <div className="rounded bg-destructive/10 px-2 sm:px-3 py-2 text-center">
            <p className="font-bold text-destructive text-sm sm:text-base">{stats.errors}</p>
            <p className="text-destructive/70 text-xs">Errors</p>
          </div>
        </div>
      </div>

      {/* Processing Queue - List View - Mobile Responsive */}
      <div className="space-y-3">
        <p className="text-xs font-semibold text-muted-foreground">PROCESSING QUEUE</p>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {displayItems.map((item, index) => (
            <div
              key={item.id}
              className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 rounded-lg border border-border bg-background/50 px-3 sm:px-4 py-3 hover:bg-background/80 transition-colors"
            >
              {/* Index & Filename Row - Mobile */}
              <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
                {/* Index */}
                <div className="flex-shrink-0">
                  <div className="flex h-7 w-7 sm:h-8 sm:w-8 items-center justify-center rounded-full bg-muted">
                    <span className="text-xs font-bold text-muted-foreground">{index + 1}</span>
                  </div>
                </div>

                {/* Info - Mobile Optimized */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-col gap-0.5 sm:gap-1">
                    <p className="text-xs sm:text-sm font-medium text-foreground truncate">
                      {item.filename}
                    </p>
                    {item.studentId && (
                      <p className="text-xs text-muted-foreground truncate">
                        {item.studentId}
                      </p>
                    )}
                  </div>
                  
                  {/* Progress Bar for processing items - Mobile */}
                  {item.status === 'processing' && item.progress !== undefined && (
                    <div className="mt-2 w-full h-1 sm:h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-300"
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Status & Result - Right Side */}
              <div className="flex items-center justify-between sm:justify-end gap-2 sm:gap-3 flex-shrink-0">
                {/* Progress Percentage */}
                {item.status === 'processing' && item.progress !== undefined && (
                  <span className="text-xs font-medium text-muted-foreground">
                    {item.progress}%
                  </span>
                )}
                
                {/* Score Display */}
                {item.status === 'done' && item.score !== undefined && (
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Score</p>
                    <p className="text-base sm:text-lg font-bold text-accent">{item.score}/40</p>
                  </div>
                )}
                
                {/* Error State */}
                {item.status === 'error' && (
                  <div className="text-right">
                    <p className="text-xs text-destructive font-medium">Failed</p>
                  </div>
                )}

                {/* Status Badge */}
                <StatusBadge status={item.status} showIcon={true} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
