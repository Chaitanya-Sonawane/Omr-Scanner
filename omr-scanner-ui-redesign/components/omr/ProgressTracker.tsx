'use client';

import { CheckCircle, Circle, Loader2 } from 'lucide-react';

interface Step {
  id: number;
  label: string;
  description?: string;
  completed: boolean;
  current: boolean;
}

interface ProgressTrackerProps {
  steps: Step[];
}

export default function ProgressTracker({ steps }: ProgressTrackerProps) {
  return (
    <div className="w-full">
      {/* Desktop: Horizontal */}
      <div className="hidden sm:block">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div key={step.id} className="flex flex-1 items-center">
              {/* Step Circle */}
              <div className="flex flex-col items-center gap-2">
                <div
                  className={`flex h-12 w-12 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                    step.completed
                      ? 'border-accent bg-accent text-white'
                      : step.current
                        ? 'border-primary bg-primary text-white animate-pulse'
                        : 'border-muted bg-background text-muted-foreground'
                  }`}
                >
                  {step.completed ? (
                    <CheckCircle className="h-6 w-6" />
                  ) : step.current ? (
                    <Loader2 className="h-6 w-6 animate-spin" />
                  ) : (
                    <Circle className="h-6 w-6" />
                  )}
                </div>
                <div className="text-center">
                  <p
                    className={`text-sm font-semibold ${
                      step.completed || step.current
                        ? 'text-foreground'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {step.label}
                  </p>
                  {step.description && (
                    <p className="text-xs text-muted-foreground">{step.description}</p>
                  )}
                </div>
              </div>

              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div className="mx-4 flex-1">
                  <div
                    className={`h-1 rounded-full transition-all duration-500 ${
                      step.completed ? 'bg-accent' : 'bg-muted'
                    }`}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Mobile: Vertical */}
      <div className="sm:hidden space-y-4">
        {steps.map((step, index) => (
          <div key={step.id}>
            <div className="flex items-start gap-3">
              {/* Step Circle */}
              <div
                className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                  step.completed
                    ? 'border-accent bg-accent text-white'
                    : step.current
                      ? 'border-primary bg-primary text-white'
                      : 'border-muted bg-background text-muted-foreground'
                }`}
              >
                {step.completed ? (
                  <CheckCircle className="h-5 w-5" />
                ) : step.current ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Circle className="h-5 w-5" />
                )}
              </div>

              {/* Step Info */}
              <div className="flex-1 pt-1">
                <p
                  className={`text-sm font-semibold ${
                    step.completed || step.current
                      ? 'text-foreground'
                      : 'text-muted-foreground'
                  }`}
                >
                  {step.label}
                </p>
                {step.description && (
                  <p className="text-xs text-muted-foreground mt-1">{step.description}</p>
                )}
              </div>
            </div>

            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div className="ml-5 mt-2 mb-2">
                <div
                  className={`w-1 h-8 rounded-full transition-all duration-500 ${
                    step.completed ? 'bg-accent' : 'bg-muted'
                  }`}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
