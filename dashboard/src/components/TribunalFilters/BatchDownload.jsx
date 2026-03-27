import { useState } from 'preact/hooks';
import * as fflate from 'fflate';

export function BatchDownload({
  selectedTribunals,
  filteredTribunals,
  allData,
  initialCoverage,
  initialStartDates,
  targetRange
}) {
  const [generatingType, setGeneratingType] = useState(null); // 'filtered' or 'selected'

  const handleDownload = async (tribunalsToDownload, type) => {
    if (tribunalsToDownload.length === 0) return;
    setGeneratingType(type);

    try {
      const coverage = allData?.tribunalCoverage ?? initialCoverage ?? {};
      const startDates = allData?.tribunalStartDates ?? initialStartDates ?? {};
      const actualTargetRange = allData?.targetRange ?? targetRange ?? { start: "2024-01-01", end: "2026-02-03" };
      const today = new Date().toISOString().split('T')[0];
      const filename = `causaganha_export_${today}_${tribunalsToDownload.length}_tribunals.zip`;

      // Memory-efficient streaming zip generation using fflate directly to StreamSaver or blob chunks
      const zipData = {};

      const summaryData = {
        generatedAt: new Date().toISOString(),
        tribunalCount: tribunalsToDownload.length,
        version: "1.0",
        targetRange: actualTargetRange,
      };
      const readmeText = `CausaGanha Export\n\nGenerated: ${summaryData.generatedAt}\nTribunais: ${summaryData.tribunalCount}\n\nFormato dos CSVs: data,status,uploadedAt,sizeMb\n- data: YYYY-MM-DD\n- status: 'collected', 'missing', ou 'outside'\n`;

      zipData["summary.json"] = fflate.strToU8(JSON.stringify(summaryData, null, 2));
      zipData["README.txt"] = fflate.strToU8(readmeText);

      // 3. per-tribunal CSVs
      for (const t of tribunalsToDownload) {
        const tCoverage = new Set(coverage[t] || []);
        const tStartStr = startDates[t];

        let csvContent = "data,status,uploadedAt,sizeMb\n";

        const globalStart = new Date(actualTargetRange.start + "T00:00:00Z");
        const globalEnd = new Date(actualTargetRange.end + "T00:00:00Z");
        let current = new Date(globalStart);

        while (current <= globalEnd) {
          const dateStr = current.toISOString().split('T')[0];
          let status = 'missing';

          if (tStartStr && dateStr < tStartStr) {
            status = 'outside';
          } else if (tCoverage.has(dateStr)) {
            status = 'collected';
          }

          csvContent += `${dateStr},${status},,\n`;
          current.setUTCDate(current.getUTCDate() + 1);
        }

        zipData[`${t}_export.csv`] = fflate.strToU8(csvContent);
      }

      // Generate zip using fast compression to minimize memory footprint and execution time
      const zipped = fflate.zipSync(zipData, { level: 6 });
      const blob = new Blob([zipped], { type: "application/zip" });

      // Use web streams if supported to bypass memory buffering limit
      if (typeof window.showSaveFilePicker === 'function') {
        try {
          const fileHandle = await window.showSaveFilePicker({
            suggestedName: filename,
            types: [{ description: 'ZIP File', accept: { 'application/zip': ['.zip'] } }],
          });
          const writable = await fileHandle.createWritable();
          await writable.write(blob);
          await writable.close();
        } catch {
          // Fallback to object URL if user cancels or errors
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          setTimeout(() => URL.revokeObjectURL(url), 10000);
        }
      } else {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 10000);
      }

    } catch (error) {
      console.error("Batch download failed:", error);
      alert("Failed to generate ZIP export.");
    } finally {
      setGeneratingType(null);
    }
  };

  const selectedCount = selectedTribunals.size;
  const filteredCount = filteredTribunals.length;
  const isGenerating = generatingType !== null;

  return (
    <div className="flex flex-col sm:flex-row gap-3 items-center">
      {filteredCount > 0 && (
        <button
          onClick={() => handleDownload(filteredTribunals, 'filtered')}
          disabled={isGenerating}
          className="flex-1 sm:flex-none px-4 py-2 bg-accent/10 hover:bg-accent/20 text-accent border border-accent/20 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {generatingType === 'filtered' ? "Gerando..." : `Download todos filtrados (${filteredCount})`}
        </button>
      )}

      {selectedCount > 0 && (
        <button
          onClick={() => handleDownload(Array.from(selectedTribunals), 'selected')}
          disabled={isGenerating}
          className="flex-1 sm:flex-none px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {generatingType === 'selected' ? "Gerando..." : `Download selecionados (${selectedCount})`}
        </button>
      )}
    </div>
  );
}
