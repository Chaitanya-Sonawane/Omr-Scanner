'use client';

interface SkeletonLoaderProps {
  count?: number;
  type?: 'card' | 'line' | 'circle' | 'grid';
  className?: string;
}

export default function SkeletonLoader({
  count = 1,
  type = 'card',
  className = '',
}: SkeletonLoaderProps) {
  const getSkeletonClass = () => {
    switch (type) {
      case 'line':
        return 'h-4 w-full rounded';
      case 'circle':
        return 'h-10 w-10 rounded-full';
      case 'grid':
        return 'h-32 w-full rounded-lg';
      default:
        return 'h-24 w-full rounded-lg';
    }
  };

  const items = Array.from({ length: count }).map((_, i) => i);

  if (type === 'grid') {
    return (
      <div className={`grid gap-4 md:grid-cols-2 lg:grid-cols-3 ${className}`}>
        {items.map((i) => (
          <div
            key={i}
            className={`bg-muted animate-pulse ${getSkeletonClass()}`}
          />
        ))}
      </div>
    );
  }

  if (type === 'line') {
    return (
      <div className={`space-y-3 ${className}`}>
        {items.map((i) => (
          <div
            key={i}
            className={`bg-muted animate-pulse ${getSkeletonClass()}`}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={`flex gap-4 ${className}`}>
      {items.map((i) => (
        <div
          key={i}
          className={`bg-muted animate-pulse ${getSkeletonClass()}`}
        />
      ))}
    </div>
  );
}
