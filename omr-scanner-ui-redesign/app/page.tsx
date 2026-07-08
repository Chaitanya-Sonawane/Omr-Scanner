'use client';

import Header from '@/components/omr/Header';
import StepIndicator from '@/components/omr/StepIndicator';
import AnswerKeySetup from '@/components/omr/steps/AnswerKeySetup';
import SheetUploadStep from '@/components/omr/steps/SheetUploadStep';
import ProcessingStep from '@/components/omr/steps/ProcessingStep';
import ResultsStep from '@/components/omr/steps/ResultsStep';
import { useOMRState } from '@/hooks/useOMRState';

export default function Page() {
  const {
    sessionId,
    answerKey,
    selectedSheets,
    processingItems,
    results,
    isProcessing,
    currentStep,
    completedSteps,
    handleAnswerKeySet,
    handleSheetsSelected,
    resetSession,
  } = useOMRState();

  const steps = [
    { id: 1, label: 'Answer Key', completed: completedSteps.includes(1), current: currentStep === 1 },
    { id: 2, label: 'Upload Sheets', completed: completedSteps.includes(2), current: currentStep === 2 },
    { id: 3, label: 'Processing', completed: completedSteps.includes(3), current: currentStep === 3 },
    { id: 4, label: 'Results', completed: completedSteps.includes(4), current: currentStep === 4 },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header sessionId={sessionId} />

      <main className="flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          {/* Step Indicator */}
          <StepIndicator steps={steps} />

          {/* Content */}
          <div className="space-y-8">
            {/* Step 1: Answer Key Setup */}
            <AnswerKeySetup
              onKeySet={handleAnswerKeySet}
              isKeySet={answerKey !== null}
            />

            {/* Step 2: Sheet Upload */}
            {answerKey && (
              <SheetUploadStep
                onSheetsSelected={handleSheetsSelected}
                isKeySet={answerKey !== null}
              />
            )}

            {/* Step 3: Processing */}
            <ProcessingStep
              items={processingItems}
              isProcessing={isProcessing}
              isVisible={selectedSheets.length > 0}
            />

            {/* Step 4: Results */}
            <ResultsStep
              results={results}
              isVisible={results.length > 0}
            />
          </div>

          {/* Empty State - Completions */}
          {completedSteps.includes(4) && (
            <div className="mt-8 rounded-xl border border-accent/20 bg-accent/5 p-6 text-center">
              <h3 className="text-lg font-bold text-foreground">Processing Complete!</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                All {results.length} sheets processed successfully.
              </p>
              <button
                onClick={resetSession}
                className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Start New Session
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/30">
        <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
          <p className="text-center text-xs text-muted-foreground">
            OMR Scanner v1.0 — Professional Optical Mark Recognition System
          </p>
        </div>
      </footer>
    </div>
  );
}
