'use client';

import { useState } from 'react';
import { Settings, FileText } from 'lucide-react';
import SettingsPanel from './SettingsPanel';

interface HeaderProps {
  sessionId?: string;
}

export default function Header({ sessionId }: HeaderProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
        <div className="flex items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-foreground">OMR Scanner</h1>
              <p className="text-xs text-muted-foreground">Optical Mark Recognition System</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {sessionId && (
              <div className="hidden sm:flex items-center gap-2" suppressHydrationWarning>
                <span className="text-sm text-muted-foreground">Session ID:</span>
                <code className="rounded bg-muted px-2 py-1 text-xs font-mono text-foreground">
                  {sessionId}
                </code>
              </div>
            )}
            <button
              onClick={() => setIsSettingsOpen(true)}
              aria-label="Settings"
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <Settings className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </>
  );
}
