'use client';

import { TrendingUp, TrendingDown, Users, Target, Award, AlertTriangle } from 'lucide-react';

interface StatisticsProps {
  totalStudents: number;
  averageScore: number;
  passRate: number;
  highestScore: number;
  lowestScore: number;
  passingThreshold?: number;
}

export default function StatisticsDashboard({
  totalStudents,
  averageScore,
  passRate,
  highestScore,
  lowestScore,
  passingThreshold = 20,
}: StatisticsProps) {
  const atRiskCount = Math.floor(totalStudents * (1 - passRate / 100));

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {/* Total Students */}
      <div className="group rounded-xl border border-border bg-card p-4 transition-all hover:border-primary hover:shadow-md">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Total Students</p>
            <p className="mt-2 text-3xl font-bold text-foreground">{totalStudents}</p>
            <p className="mt-1 text-xs text-muted-foreground">Processed sheets</p>
          </div>
          <div className="rounded-lg bg-primary/10 p-3">
            <Users className="h-6 w-6 text-primary" />
          </div>
        </div>
      </div>

      {/* Average Score */}
      <div className="group rounded-xl border border-border bg-card p-4 transition-all hover:border-accent hover:shadow-md">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Average Score</p>
            <p className="mt-2 text-3xl font-bold text-foreground">{averageScore.toFixed(1)}</p>
            <p className="mt-1 text-xs text-accent flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              {((averageScore / 40) * 100).toFixed(1)}% overall
            </p>
          </div>
          <div className="rounded-lg bg-accent/10 p-3">
            <Target className="h-6 w-6 text-accent" />
          </div>
        </div>
      </div>

      {/* Pass Rate */}
      <div className="group rounded-xl border border-border bg-card p-4 transition-all hover:border-accent hover:shadow-md">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Pass Rate</p>
            <p className="mt-2 text-3xl font-bold text-foreground">{passRate.toFixed(0)}%</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {Math.floor((totalStudents * passRate) / 100)} of {totalStudents} students
            </p>
          </div>
          <div className="rounded-lg bg-accent/10 p-3">
            <Award className="h-6 w-6 text-accent" />
          </div>
        </div>
      </div>

      {/* Highest Score */}
      <div className="group rounded-xl border border-border bg-card p-4 transition-all hover:border-primary hover:shadow-md">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Highest Score</p>
            <p className="mt-2 text-3xl font-bold text-primary">{highestScore}</p>
            <p className="mt-1 text-xs text-primary flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              Top performer
            </p>
          </div>
          <div className="rounded-lg bg-primary/10 p-3">
            <Award className="h-6 w-6 text-primary" />
          </div>
        </div>
      </div>

      {/* Lowest Score */}
      <div className="group rounded-xl border border-border bg-card p-4 transition-all hover:border-warning hover:shadow-md">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Lowest Score</p>
            <p className="mt-2 text-3xl font-bold text-warning">{lowestScore}</p>
            <p className="mt-1 text-xs text-warning flex items-center gap-1">
              <TrendingDown className="h-3 w-3" />
              Needs attention
            </p>
          </div>
          <div className="rounded-lg bg-warning/10 p-3">
            <AlertTriangle className="h-6 w-6 text-warning" />
          </div>
        </div>
      </div>

      {/* At Risk */}
      {atRiskCount > 0 && (
        <div className="group rounded-xl border border-destructive/30 bg-destructive/5 p-4 transition-all hover:border-destructive hover:shadow-md">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">At Risk</p>
              <p className="mt-2 text-3xl font-bold text-destructive">{atRiskCount}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Below {passingThreshold} points
              </p>
            </div>
            <div className="rounded-lg bg-destructive/10 p-3">
              <AlertTriangle className="h-6 w-6 text-destructive" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
