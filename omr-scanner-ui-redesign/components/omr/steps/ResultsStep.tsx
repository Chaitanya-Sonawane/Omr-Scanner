'use client';

import { useState, useMemo } from 'react';
import { ChevronDown, Download, Filter, Search, Printer, FileSpreadsheet, FileText } from 'lucide-react';
import ChartVisualization from '../ChartVisualization';
import StatisticsDashboard from '../StatisticsDashboard';
import QuickActions from '../QuickActions';

interface StudentResult {
  id: string;
  name: string;
  score: number;
  intelligence: number;
  science: number;
  social: number;
  math: number;
  answers: { [key: number]: { marked: string; correct: string } };
}

interface ResultsStepProps {
  results?: StudentResult[];
  isVisible?: boolean;
}

export default function ResultsStep({
  results = [],
  isVisible = false,
}: ResultsStepProps) {
  const [sortBy, setSortBy] = useState<'score' | 'name'>('score');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'pass' | 'fail'>('all');
  const [showCharts, setShowCharts] = useState(false);

  if (!isVisible || results.length === 0) {
    return null;
  }

  // Filter and search logic
  const filteredResults = useMemo(() => {
    return results.filter((result) => {
      const matchesSearch = 
        result.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        result.id.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesFilter = 
        filterStatus === 'all' ? true :
        filterStatus === 'pass' ? result.score >= 20 :
        result.score < 20;
      
      return matchesSearch && matchesFilter;
    });
  }, [results, searchQuery, filterStatus]);

  const sortedResults = useMemo(() => {
    return [...filteredResults].sort((a, b) => {
      if (sortBy === 'score') return b.score - a.score;
      return a.name.localeCompare(b.name);
    });
  }, [filteredResults, sortBy]);

  const avgScore = Math.round(
    results.reduce((sum, r) => sum + r.score, 0) / results.length
  );
  const passRate = Math.round(
    ((results.filter((r) => r.score >= 20).length / results.length) * 100)
  );
  
  const highestScore = Math.max(...results.map(r => r.score));
  const lowestScore = Math.min(...results.map(r => r.score));

  const handleExportPDF = () => {
    // Download PDF from backend API
    const sessionId = 'current_session'; // Get from context/state
    window.open(`http://localhost:8000/api/session/${sessionId}/export/pdf`, '_blank');
  };

  const handleExportExcel = () => {
    // Download Excel from backend API
    const sessionId = 'current_session'; // Get from context/state
    window.open(`http://localhost:8000/api/session/${sessionId}/export/excel`, '_blank');
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4 sm:p-6">
      <div className="flex items-center justify-between mb-4 sm:mb-6">
        <h2 className="text-lg sm:text-xl font-bold text-foreground">Step 4: Results</h2>
        <button
          onClick={() => setShowCharts(!showCharts)}
          className="text-xs sm:text-sm font-semibold text-primary hover:text-primary/80 transition-colors"
        >
          {showCharts ? 'Hide' : 'Show'} Analytics
        </button>
      </div>

      {/* Charts Section */}
      {showCharts && (
        <div className="mb-6 sm:mb-8 animate-in fade-in duration-300">
          <ChartVisualization results={results} />
        </div>
      )}

      {/* Enhanced Statistics Dashboard */}
      <div className="mb-6 sm:mb-8">
        <StatisticsDashboard
          totalStudents={results.length}
          averageScore={avgScore}
          passRate={passRate}
          highestScore={highestScore}
          lowestScore={lowestScore}
          passingThreshold={20}
        />
      </div>

      {/* Quick Actions */}
      <div className="mb-6 sm:mb-8">
        <QuickActions
          onExportCSV={handleExportExcel}
          onPrint={handleExportPDF}
          onRefresh={() => window.location.reload()}
        />
      </div>

      {/* Search and Filters - Enhanced */}
      <div className="mb-4 sm:mb-6 space-y-3">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by name or student ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-border bg-background pl-10 pr-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {/* Filters Row */}
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          <Filter className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground flex-shrink-0" />
          
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'score' | 'name')}
            className="flex-1 sm:flex-initial min-w-0 sm:min-w-[150px] rounded-lg border border-border bg-background px-2.5 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-foreground hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="score">Sort by Score</option>
            <option value="name">Sort by Name</option>
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as 'all' | 'pass' | 'fail')}
            className="flex-1 sm:flex-initial min-w-0 sm:min-w-[150px] rounded-lg border border-border bg-background px-2.5 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-foreground hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="all">All Students ({results.length})</option>
            <option value="pass">Pass ({results.filter(r => r.score >= 20).length})</option>
            <option value="fail">Fail ({results.filter(r => r.score < 20).length})</option>
          </select>
        </div>

        {/* Results Count */}
        {searchQuery && (
          <p className="text-xs text-muted-foreground">
            Showing {sortedResults.length} of {results.length} results
          </p>
        )}
      </div>

      {/* Results Table - Desktop Only */}
      <div className="hidden sm:block sm:overflow-x-auto sm:rounded-lg sm:border sm:border-border" suppressHydrationWarning>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">
                Student
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground">
                Total
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground">
                Intelligence
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground">
                Science
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground">
                Social
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground">
                Math
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground">
                Details
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sortedResults.map((result, idx) => (
              <tbody key={result.id}>
                <tr className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/20'}>
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">{result.name}</p>
                      <p className="text-xs text-muted-foreground">{result.id}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="rounded-lg bg-primary/10 px-3 py-1.5 text-sm font-bold text-primary">
                      {result.score}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-sm font-medium text-foreground">
                    {result.intelligence}
                  </td>
                  <td className="px-4 py-3 text-center text-sm font-medium text-foreground">
                    {result.science}
                  </td>
                  <td className="px-4 py-3 text-center text-sm font-medium text-foreground">
                    {result.social}
                  </td>
                  <td className="px-4 py-3 text-center text-sm font-medium text-foreground">
                    {result.math}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() =>
                        setExpandedId(expandedId === result.id ? null : result.id)
                      }
                      className="inline-flex items-center justify-center text-muted-foreground hover:text-primary transition-colors"
                    >
                      <ChevronDown
                        className={`h-4 w-4 transition-transform ${
                          expandedId === result.id ? 'rotate-180' : ''
                        }`}
                      />
                    </button>
                  </td>
                </tr>

                {/* Expanded Row - Answer Details Desktop */}
                {expandedId === result.id && (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 bg-muted/10">
                      <div>
                        <h4 className="text-sm font-semibold text-foreground mb-4">
                          Answer Details
                        </h4>
                        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                          {Object.entries(result.answers).map(([qNum, answer]) => {
                            const isCorrect = answer.marked === answer.correct;
                            return (
                              <div
                                key={qNum}
                                className={`rounded-lg border px-3 py-2 ${
                                  isCorrect
                                    ? 'border-accent/30 bg-accent/10'
                                    : answer.marked === ''
                                      ? 'border-yellow-500/30 bg-yellow-500/10'
                                      : 'border-destructive/30 bg-destructive/10'
                                }`}
                              >
                                <p className="text-xs text-muted-foreground mb-1">
                                  Question {qNum}
                                </p>
                                <div className="space-y-1 text-xs font-medium">
                                  <p className={isCorrect ? 'text-accent' : 'text-foreground'}>
                                    Marked: <span className="font-bold">{answer.marked || '—'}</span>
                                  </p>
                                  {!isCorrect && (
                                    <p className="text-muted-foreground">
                                      Correct: <span className="text-accent">{answer.correct}</span>
                                    </p>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="space-y-3 sm:hidden" suppressHydrationWarning>
        {sortedResults.map((result) => (
          <div key={result.id} className="rounded-lg border border-border bg-background/50 p-3 space-y-3">
            {/* Header */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-foreground truncate">{result.name}</p>
                <p className="text-xs text-muted-foreground truncate">{result.id}</p>
              </div>
              <span className="rounded-lg bg-primary/10 px-2.5 py-1 text-sm font-bold text-primary flex-shrink-0">
                {result.score}/40
              </span>
            </div>

            {/* Scores Grid */}
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="rounded bg-muted/50 px-2 py-2">
                <p className="text-xs text-muted-foreground mb-0.5">Intelligence</p>
                <p className="text-base font-bold text-foreground">{result.intelligence}</p>
              </div>
              <div className="rounded bg-muted/50 px-2 py-2">
                <p className="text-xs text-muted-foreground mb-0.5">Science</p>
                <p className="text-base font-bold text-foreground">{result.science}</p>
              </div>
              <div className="rounded bg-muted/50 px-2 py-2">
                <p className="text-xs text-muted-foreground mb-0.5">Social</p>
                <p className="text-base font-bold text-foreground">{result.social}</p>
              </div>
              <div className="rounded bg-muted/50 px-2 py-2">
                <p className="text-xs text-muted-foreground mb-0.5">Math</p>
                <p className="text-base font-bold text-foreground">{result.math}</p>
              </div>
            </div>

            {/* Expand Button */}
            <button
              onClick={() =>
                setExpandedId(expandedId === result.id ? null : result.id)
              }
              className="w-full flex items-center justify-center gap-2 text-xs font-semibold text-primary hover:text-primary/80 transition-colors py-2"
            >
              <span>{expandedId === result.id ? 'Hide' : 'Show'} Answer Details</span>
              <ChevronDown
                className={`h-3.5 w-3.5 transition-transform ${
                  expandedId === result.id ? 'rotate-180' : ''
                }`}
              />
            </button>

            {/* Mobile Answer Details */}
            {expandedId === result.id && (
              <div className="space-y-2 border-t border-border pt-3">
                <h4 className="text-xs font-semibold text-foreground">Answer Details</h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {Object.entries(result.answers).map(([qNum, answer]) => {
                    const isCorrect = answer.marked === answer.correct;
                    return (
                      <div
                        key={qNum}
                        className={`rounded border px-2 py-1.5 text-xs ${
                          isCorrect
                            ? 'border-accent/30 bg-accent/10'
                            : answer.marked === ''
                              ? 'border-yellow-500/30 bg-yellow-500/10'
                              : 'border-destructive/30 bg-destructive/10'
                        }`}
                      >
                        <p className="text-muted-foreground mb-0.5">Q{qNum}</p>
                        <div className="flex justify-between gap-2">
                          <span className={isCorrect ? 'text-accent font-bold' : 'text-foreground'}>
                            Marked: {answer.marked || '—'}
                          </span>
                          {!isCorrect && (
                            <span className="text-accent font-bold">
                              Correct: {answer.correct}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Add this style tag for print layout
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @media print {
      body * {
        visibility: hidden;
      }
      .print-section, .print-section * {
        visibility: visible;
      }
      .print-section {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
      }
      @page {
        margin: 1cm;
      }
    }
  `;
  if (!document.head.querySelector('style[data-print-styles]')) {
    style.setAttribute('data-print-styles', 'true');
    document.head.appendChild(style);
  }
}
