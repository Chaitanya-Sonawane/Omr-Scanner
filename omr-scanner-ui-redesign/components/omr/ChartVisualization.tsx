'use client';

import { BarChart3, TrendingUp, PieChart } from 'lucide-react';

interface ChartVisualizationProps {
  results: Array<{
    score: number;
    studentId?: string;
  }>;
}

export default function ChartVisualization({ results }: ChartVisualizationProps) {
  // Calculate statistics
  const scores = results.map(r => r.score);
  const average = scores.reduce((a, b) => a + b, 0) / scores.length;
  const passRate = (scores.filter(s => s >= 24).length / scores.length) * 100;
  
  // Score distribution buckets
  const distribution = {
    excellent: scores.filter(s => s >= 36).length, // 90%+
    good: scores.filter(s => s >= 32 && s < 36).length, // 80-89%
    average: scores.filter(s => s >= 24 && s < 32).length, // 60-79%
    poor: scores.filter(s => s < 24).length, // <60%
  };

  const maxCount = Math.max(...Object.values(distribution));

  return (
    <div className="space-y-6">
      {/* Score Distribution Chart */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-bold text-foreground">Score Distribution</h3>
        </div>

        <div className="space-y-3">
          {/* Excellent */}
          <div className="flex items-center gap-3">
            <div className="w-20 text-sm font-medium text-foreground">Excellent</div>
            <div className="flex-1">
              <div className="relative h-8 rounded-lg bg-muted overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-green-500 to-green-600 transition-all duration-500 flex items-center justify-end px-3"
                  style={{ width: `${(distribution.excellent / maxCount) * 100}%` }}
                >
                  <span className="text-xs font-bold text-white">{distribution.excellent}</span>
                </div>
              </div>
            </div>
            <div className="w-16 text-xs text-muted-foreground text-right">90-100%</div>
          </div>

          {/* Good */}
          <div className="flex items-center gap-3">
            <div className="w-20 text-sm font-medium text-foreground">Good</div>
            <div className="flex-1">
              <div className="relative h-8 rounded-lg bg-muted overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500 flex items-center justify-end px-3"
                  style={{ width: `${(distribution.good / maxCount) * 100}%` }}
                >
                  <span className="text-xs font-bold text-white">{distribution.good}</span>
                </div>
              </div>
            </div>
            <div className="w-16 text-xs text-muted-foreground text-right">80-89%</div>
          </div>

          {/* Average */}
          <div className="flex items-center gap-3">
            <div className="w-20 text-sm font-medium text-foreground">Average</div>
            <div className="flex-1">
              <div className="relative h-8 rounded-lg bg-muted overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-yellow-500 to-yellow-600 transition-all duration-500 flex items-center justify-end px-3"
                  style={{ width: `${(distribution.average / maxCount) * 100}%` }}
                >
                  <span className="text-xs font-bold text-white">{distribution.average}</span>
                </div>
              </div>
            </div>
            <div className="w-16 text-xs text-muted-foreground text-right">60-79%</div>
          </div>

          {/* Poor */}
          <div className="flex items-center gap-3">
            <div className="w-20 text-sm font-medium text-foreground">Below Avg</div>
            <div className="flex-1">
              <div className="relative h-8 rounded-lg bg-muted overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-red-500 to-red-600 transition-all duration-500 flex items-center justify-end px-3"
                  style={{ width: `${(distribution.poor / maxCount) * 100}%` }}
                >
                  <span className="text-xs font-bold text-white">{distribution.poor}</span>
                </div>
              </div>
            </div>
            <div className="w-16 text-xs text-muted-foreground text-right">&lt;60%</div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Average Trend */}
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-2 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-accent" />
            <span className="text-sm font-medium text-muted-foreground">Class Average</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-foreground">{average.toFixed(1)}</span>
            <span className="text-sm text-muted-foreground">/ 40</span>
          </div>
          <div className="mt-1 text-xs text-accent font-medium">
            {((average / 40) * 100).toFixed(1)}% overall
          </div>
        </div>

        {/* Pass Rate */}
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-2 flex items-center gap-2">
            <PieChart className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-muted-foreground">Pass Rate</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-foreground">{passRate.toFixed(0)}%</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {scores.filter(s => s >= 24).length} of {scores.length} students
          </div>
        </div>
      </div>
    </div>
  );
}
