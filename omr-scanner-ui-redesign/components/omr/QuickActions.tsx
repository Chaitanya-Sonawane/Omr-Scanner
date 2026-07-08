'use client';

import { Download, Printer, Share2, RefreshCw, FileSpreadsheet } from 'lucide-react';

interface QuickActionsProps {
  onExportCSV?: () => void;
  onPrint?: () => void;
  onShare?: () => void;
  onRefresh?: () => void;
  disabled?: boolean;
}

export default function QuickActions({
  onExportCSV,
  onPrint,
  onShare,
  onRefresh,
  disabled = false,
}: QuickActionsProps) {
  const actions = [
    {
      icon: FileSpreadsheet,
      label: 'Export CSV',
      onClick: onExportCSV,
      color: 'text-accent',
    },
    {
      icon: Printer,
      label: 'Print',
      onClick: onPrint,
      color: 'text-primary',
    },
    {
      icon: Share2,
      label: 'Share',
      onClick: onShare,
      color: 'text-muted-foreground',
    },
    {
      icon: RefreshCw,
      label: 'Refresh',
      onClick: onRefresh,
      color: 'text-warning',
    },
  ];

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {actions.map((action) => {
        const Icon = action.icon;
        return (
          <button
            key={action.label}
            onClick={action.onClick}
            disabled={disabled || !action.onClick}
            className={`group inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium transition-all hover:border-primary hover:bg-primary/5 disabled:opacity-50 disabled:cursor-not-allowed ${action.color}`}
            title={action.label}
          >
            <Icon className="h-4 w-4" />
            <span className="hidden sm:inline">{action.label}</span>
          </button>
        );
      })}
    </div>
  );
}
