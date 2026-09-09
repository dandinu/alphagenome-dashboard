const MODALITY_LABELS: Record<string, string> = {
  splicing: 'Splicing',
  expression: 'Expression',
  chromatin: 'Chromatin',
  tf_binding: 'TF Binding',
  histone: 'Histone',
  protein: 'Protein (AlphaMissense)',
  conservation: 'Conservation',
};

const MODALITY_COLORS: Record<string, string> = {
  splicing: 'bg-purple-500',
  expression: 'bg-blue-500',
  chromatin: 'bg-teal-500',
  tf_binding: 'bg-amber-500',
  histone: 'bg-pink-500',
  protein: 'bg-red-500',
  conservation: 'bg-gray-500',
};

interface AttributionBreakdownProps {
  attributions: Record<string, number>;
  threshold?: number;
}

export default function AttributionBreakdown({
  attributions,
  threshold = 0.15,
}: AttributionBreakdownProps) {
  const entries = Object.entries(attributions).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-2">
      {entries.map(([modality, share]) => (
        <div key={modality} className="flex items-center gap-3">
          <div className="w-40 shrink-0 text-sm text-gray-600">
            {MODALITY_LABELS[modality] ?? modality}
          </div>
          <div className="relative h-4 flex-1 overflow-hidden rounded bg-gray-100">
            <div
              className={`h-full rounded ${MODALITY_COLORS[modality] ?? 'bg-gray-400'} ${
                share >= threshold ? '' : 'opacity-40'
              }`}
              style={{ width: `${Math.max(share * 100, 0.5)}%` }}
            />
            {/* triage threshold marker */}
            <div
              className="absolute top-0 h-full w-px bg-gray-400"
              style={{ left: `${threshold * 100}%` }}
              title={`Triage threshold (${Math.round(threshold * 100)}%)`}
            />
          </div>
          <div className="w-12 shrink-0 text-right text-sm font-medium text-gray-700">
            {(share * 100).toFixed(1)}%
          </div>
        </div>
      ))}
    </div>
  );
}
