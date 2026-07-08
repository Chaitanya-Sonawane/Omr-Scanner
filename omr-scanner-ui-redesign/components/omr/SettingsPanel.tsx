'use client';

import { useState } from 'react';
import { Settings, X, Moon, Sun, Save } from 'lucide-react';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const [passingScore, setPassingScore] = useState(20);
  const [darkMode, setDarkMode] = useState(false);
  const [autoExport, setAutoExport] = useState(false);
  const [showNotifications, setShowNotifications] = useState(true);

  const handleSave = () => {
    // Save settings to localStorage
    const settings = {
      passingScore,
      darkMode,
      autoExport,
      showNotifications,
    };
    localStorage.setItem('omr-settings', JSON.stringify(settings));
    
    // Apply dark mode
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 animate-in fade-in duration-200"
        onClick={onClose}
      />
      
      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 w-full sm:w-96 bg-card border-l border-border z-50 animate-in slide-in-from-right duration-300 overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Settings className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-bold text-foreground">Settings</h2>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 hover:bg-muted transition-colors"
              aria-label="Close settings"
            >
              <X className="h-5 w-5 text-muted-foreground" />
            </button>
          </div>

          {/* Settings Sections */}
          <div className="space-y-6">
            {/* Grading Settings */}
            <section className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Grading</h3>
              
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">
                  Passing Score (out of 40)
                </label>
                <input
                  type="number"
                  min="0"
                  max="40"
                  value={passingScore}
                  onChange={(e) => setPassingScore(Number(e.target.value))}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <p className="text-xs text-muted-foreground">
                  Students need at least {passingScore} points to pass
                </p>
              </div>
            </section>

            {/* Appearance */}
            <section className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Appearance</h3>
              
              <div className="flex items-center justify-between rounded-lg border border-border bg-background p-3">
                <div className="flex items-center gap-3">
                  {darkMode ? (
                    <Moon className="h-4 w-4 text-primary" />
                  ) : (
                    <Sun className="h-4 w-4 text-primary" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-foreground">Dark Mode</p>
                    <p className="text-xs text-muted-foreground">Toggle dark theme</p>
                  </div>
                </div>
                <button
                  onClick={() => setDarkMode(!darkMode)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    darkMode ? 'bg-primary' : 'bg-muted'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      darkMode ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </section>

            {/* Export Settings */}
            <section className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Export</h3>
              
              <div className="flex items-center justify-between rounded-lg border border-border bg-background p-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Auto Export</p>
                  <p className="text-xs text-muted-foreground">Export results after processing</p>
                </div>
                <button
                  onClick={() => setAutoExport(!autoExport)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    autoExport ? 'bg-primary' : 'bg-muted'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      autoExport ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </section>

            {/* Notifications */}
            <section className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Notifications</h3>
              
              <div className="flex items-center justify-between rounded-lg border border-border bg-background p-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Show Notifications</p>
                  <p className="text-xs text-muted-foreground">Processing status alerts</p>
                </div>
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    showNotifications ? 'bg-primary' : 'bg-muted'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      showNotifications ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </section>

            {/* About */}
            <section className="space-y-2 rounded-lg border border-border bg-muted/30 p-4">
              <h3 className="text-sm font-semibold text-foreground">About</h3>
              <p className="text-xs text-muted-foreground">
                OMR Scanner v1.0
              </p>
              <p className="text-xs text-muted-foreground">
                Professional Optical Mark Recognition System
              </p>
            </section>
          </div>

          {/* Save Button */}
          <button
            onClick={handleSave}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Save className="h-4 w-4" />
            Save Settings
          </button>
        </div>
      </div>
    </>
  );
}
