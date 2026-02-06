export function SkeletonLoader({ className = "" }) {
  return (
    <div
      className={`animate-pulse bg-gradient-to-r from-cyber-dark via-cyber-dim/30 to-cyber-dark bg-[length:200%_100%] rounded ${className}`}
      style={{
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
    <div className={`bg-cyber-card border border-cyber-border p-6 rounded shadow-glow ${className}`}>
      {children}
    </div>
  );
}
