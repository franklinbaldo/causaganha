export function SkeletonLoader({ className = "" }) {
  return (
    <div
      className={`bg-surface-overlay rounded animate-pulse ${className}`}
      style={{
        backgroundImage: 'linear-gradient(90deg, var(--color-surface-overlay) 0%, var(--color-surface) 50%, var(--color-surface-overlay) 100%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 2s ease-in-out infinite',
      }}
    />
  );
}

export function SkeletonText({ width = "w-full", height = "h-4", className = "" }) {
  return <SkeletonLoader className={`${width} ${height} ${className}`} />;
}

export function SkeletonCard({ children, className = "" }) {
  return (
    <div className={`card ${className}`}>
      {children}
    </div>
  );
}
