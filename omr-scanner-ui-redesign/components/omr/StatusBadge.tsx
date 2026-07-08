'use client';

import { AlertCircle, CheckCircle, Clock, Loader2 } from 'lucide-react';

type StatusType = 'queued' | 'processing' | 'done' | 'error';

interface StatusBadgeProps {
  status: StatusType;
  showIcon?: boolean;
}

const statusConfig = {
  queued: {
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    icon: Clock,
    label: 'Queued',
  },
  processing: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-700 dark:text-blue-300',
    icon: Loader2,
    label: 'Processing',
    animate: true,
  },
  done: {
    bg: 'bg-accent/20',
    text: 'text-accent',
    icon: CheckCircle,
    label: 'Complete',
  },
  error: {
    bg: 'bg-destructive/10',
    text: 'text-destructive',
    icon: AlertCircle,
    label: 'Error',
  },
};

export default function StatusBadge({ status, showIcon = true }: StatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${config.bg} ${config.text}`}
    >
      {showIcon && (
        <Icon className={`h-3.5 w-3.5 ${config.animate ? 'animate-spin' : ''}`} />
      )}
      {config.label}
    </div>
  );
}
