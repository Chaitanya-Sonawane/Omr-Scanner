'use client';

import { Check } from 'lucide-react';

interface Step {
  id: number;
  label: string;
  completed: boolean;
  current: boolean;
}

interface StepIndicatorProps {
  steps: Step[];
}

export default function StepIndicator({ steps }: StepIndicatorProps) {
  return (
    <nav aria-label="Progress" className="mb-8">
      <ol className="flex items-center">
        {steps.map((step, idx) => (
          <li key={step.id} className="flex flex-1 items-center">
            <div className="flex flex-col items-center flex-1">
              <div
                className={`relative flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all ${
                  step.completed
                    ? 'border-accent bg-accent text-accent-foreground'
                    : step.current
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-card text-muted-foreground'
                }`}
              >
                {step.completed ? (
                  <Check className="h-5 w-5" />
                ) : (
                  <span className="text-sm font-semibold">{step.id}</span>
                )}
              </div>
              <span
                className={`mt-2 text-xs font-medium sm:text-sm ${
                  step.current
                    ? 'text-primary'
                    : step.completed
                      ? 'text-accent'
                      : 'text-muted-foreground'
                }`}
              >
                {step.label}
              </span>
            </div>

            {idx < steps.length - 1 && (
              <div
                className={`mx-2 h-1 flex-1 rounded-full transition-all ${
                  step.completed ? 'bg-accent' : 'bg-border'
                }`}
              />
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
