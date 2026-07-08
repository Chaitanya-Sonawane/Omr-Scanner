'use client';

import { useState, useCallback, useRef, useEffect } from 'react';

export interface ProcessingItem {
  id: string;
  filename: string;
  studentId?: string;
  status: 'queued' | 'processing' | 'done' | 'error';
  score?: number;
  progress?: number;
}

export interface StudentResult {
  id: string;
  name: string;
  score: number;
  intelligence: number;
  science: number;
  social: number;
  math: number;
  answers: { [key: number]: { marked: string; correct: string } };
}

export function useOMRState() {
  const [sessionId, setSessionId] = useState('');
  const [answerKey, setAnswerKey] = useState<{ [key: number]: string } | null>(null);
  const [selectedSheets, setSelectedSheets] = useState<File[]>([]);
  const [processingItems, setProcessingItems] = useState<ProcessingItem[]>([]);
  const [results, setResults] = useState<StudentResult[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  const processingIntervals = useRef<NodeJS.Timeout[]>([]);

  useEffect(() => {
    setSessionId('sess_' + Math.random().toString(36).substring(7));
  }, []);

  const handleAnswerKeySet = useCallback((key: { [key: number]: string }) => {
    setAnswerKey(key);
    setCompletedSteps((prev) => [...new Set([...prev, 1])]);
    setCurrentStep(2);
  }, []);

  const handleSheetsSelected = useCallback(
    (files: File[], studentInfo?: { [filename: string]: string }) => {
      setSelectedSheets(files);
      setCompletedSteps((prev) => [...new Set([...prev, 2])]);
      setCurrentStep(3);
      simulateProcessing(files, studentInfo, answerKey);
    },
    [answerKey]
  );

  const simulateProcessing = (
    files: File[],
    studentInfo?: { [filename: string]: string },
    key?: { [key: number]: string } | null
  ) => {
    setIsProcessing(true);

    const items: ProcessingItem[] = files.map((file, idx) => ({
      id: `sheet_${idx}`,
      filename: file.name,
      studentId: studentInfo?.[file.name] || `Student ${idx + 1}`,
      status: 'queued' as const,
      progress: 0,
    }));

    setProcessingItems(items);

    let processedCount = 0;

    files.forEach((file, idx) => {
      const delay = setTimeout(() => {
        setProcessingItems((prev) =>
          prev.map((item, i) =>
            i === idx ? { ...item, status: 'processing' as const, progress: 0 } : item
          )
        );

        let progress = 0;
        const progressInterval = setInterval(() => {
          progress += Math.random() * 30;
          if (progress >= 100) {
            clearInterval(progressInterval);
            progress = 100;

            setProcessingItems((prev) =>
              prev.map((item, i) => {
                if (i === idx) {
                  const score = Math.floor(Math.random() * 40) + 1;
                  return {
                    ...item,
                    status: 'done' as const,
                    score,
                    progress: 100,
                  };
                }
                return item;
              })
            );

            processedCount++;
            if (processedCount === files.length) {
              handleProcessingComplete(key);
            }
          } else {
            setProcessingItems((prev) =>
              prev.map((item, i) =>
                i === idx ? { ...item, progress: Math.min(progress, 99) } : item
              )
            );
          }
        }, 400);

        processingIntervals.current.push(progressInterval);
      }, idx * 800);

      processingIntervals.current.push(delay);
    });
  };

  const handleProcessingComplete = (key?: { [key: number]: string } | null) => {
    setIsProcessing(false);
    setCompletedSteps((prev) => [...new Set([...prev, 3])]);
    setCurrentStep(4);

    const mockResults: StudentResult[] = processingItems.map((item) => ({
      id: item.studentId || 'Unknown',
      name: item.studentId || item.filename.split('.')[0],
      score: item.score || Math.floor(Math.random() * 40) + 1,
      intelligence: Math.floor(Math.random() * 10) + 1,
      science: Math.floor(Math.random() * 10) + 1,
      social: Math.floor(Math.random() * 10) + 1,
      math: Math.floor(Math.random() * 10) + 1,
      answers: Object.fromEntries(
        Array.from({ length: 40 }, (_, i) => {
          const marked = ['A', 'B', 'C', 'D'][Math.floor(Math.random() * 4)];
          const correct = key?.[i + 1] || 'A';
          return [i + 1, { marked, correct }];
        })
      ),
    }));

    setResults(mockResults);
    setCompletedSteps((prev) => [...new Set([...prev, 4])]);
  };

  const resetSession = useCallback(() => {
    processingIntervals.current.forEach(clearInterval);
    processingIntervals.current = [];
    setAnswerKey(null);
    setSelectedSheets([]);
    setProcessingItems([]);
    setResults([]);
    setCompletedSteps([]);
    setCurrentStep(1);
  }, []);

  return {
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
  };
}
