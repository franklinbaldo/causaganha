export function FilterPanel({ filters, setFilters, filteredCount, totalCount }) {
  const handleChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleCoverageChange = (index, value) => {
    const newRange = [...filters.coverageRange];
    newRange[index] = Number(value);
    if (newRange[0] > newRange[1]) {
      // Auto correct if crossed
      if (index === 0) newRange[1] = newRange[0];
      else newRange[0] = newRange[1];
    }
    setFilters(prev => ({ ...prev, coverageRange: newRange }));
  };

  const handleDateChange = (key, value) => {
    setFilters(prev => ({ ...prev, dateRange: { ...prev.dateRange, [key]: value } }));
  };

  return (
    <div className="card p-4 flex flex-col gap-4 mb-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
        <h3 className="text-lg font-semibold text-black dark:text-white">Filtros Avançados</h3>
        <span className="text-sm font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-slate-800 px-3 py-1 rounded-full">
          {filteredCount} de {totalCount} tribunais
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Date Range */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Data (Início - Fim)</label>
          <div className="flex gap-2 items-center">
            <input
              type="date"
              className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-2 py-1 text-sm text-black dark:text-white focus:outline-none focus:border-accent"
              value={filters.dateRange.start}
              onChange={(e) => handleDateChange('start', e.target.value)}
            />
            <span className="text-gray-400">-</span>
            <input
              type="date"
              className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-2 py-1 text-sm text-black dark:text-white focus:outline-none focus:border-accent"
              value={filters.dateRange.end}
              onChange={(e) => handleDateChange('end', e.target.value)}
            />
          </div>
        </div>

        {/* Coverage Slider */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Cobertura: {filters.coverageRange[0]}% - {filters.coverageRange[1]}%
          </label>
          <div className="flex gap-2 items-center">
            <input
              type="range"
              min="0"
              max="100"
              className="w-full"
              value={filters.coverageRange[0]}
              onChange={(e) => handleCoverageChange(0, e.target.value)}
            />
            <input
              type="range"
              min="0"
              max="100"
              className="w-full"
              value={filters.coverageRange[1]}
              onChange={(e) => handleCoverageChange(1, e.target.value)}
            />
          </div>
        </div>

        {/* Velocity Trend Select */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Tendência de Velocidade</label>
          <select
            className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-black dark:text-white focus:outline-none focus:border-accent"
            value={filters.velocityTrend}
            onChange={(e) => handleChange('velocityTrend', e.target.value)}
          >
            <option value="all">Todas</option>
            <option value="accelerating">Acelerando</option>
            <option value="stable">Estável</option>
            <option value="decelerating">Desacelerando</option>
          </select>
        </div>

        {/* Gap Pattern Toggle & Status */}
        <div className="flex flex-col gap-2 justify-between">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Status</label>
            <select
              className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-black dark:text-white focus:outline-none focus:border-accent"
              value={filters.status}
              onChange={(e) => handleChange('status', e.target.value)}
            >
              <option value="all">Todos</option>
              <option value="active">Ativos</option>
              <option value="inactive">Inativos</option>
            </select>
          </div>

          <label className="flex items-center gap-2 cursor-pointer mt-1">
            <input
              type="checkbox"
              className="rounded border-gray-300 text-accent focus:ring-accent w-4 h-4 cursor-pointer"
              checked={filters.gapPattern}
              onChange={(e) => handleChange('gapPattern', e.target.checked)}
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Possui falhas {'>'}7 dias</span>
          </label>
        </div>
      </div>
    </div>
  );
}
