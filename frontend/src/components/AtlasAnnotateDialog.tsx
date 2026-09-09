import { useState } from 'react';
import { X, Sparkles, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useStartAtlasAnnotation, useAtlasJobStatus, useLoadedFiles } from '../hooks/useApi';
import type { AtlasAnnotateOptions } from '../types';

interface AtlasAnnotateDialogProps {
  open: boolean;
  onClose: () => void;
  defaultVcfFileId?: number;
}

export default function AtlasAnnotateDialog({
  open,
  onClose,
  defaultVcfFileId,
}: AtlasAnnotateDialogProps) {
  const { data: loadedFiles } = useLoadedFiles();
  const [vcfFileId, setVcfFileId] = useState<number | undefined>(defaultVcfFileId);
  const [options, setOptions] = useState<AtlasAnnotateOptions>({
    non_ref_only: true,
    pass_only: true,
    coding_only: false,
    overwrite: false,
  });
  const [minQuality, setMinQuality] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);

  const startMutation = useStartAtlasAnnotation();
  const { data: job } = useAtlasJobStatus(jobId);

  if (!open) return null;

  const files = loadedFiles?.files ?? [];
  const effectiveFileId = vcfFileId ?? files[0]?.id;
  const isRunning = job?.status === 'running' || job?.status === 'queued';

  const handleStart = () => {
    if (!effectiveFileId) return;
    startMutation.mutate(
      {
        vcfFileId: effectiveFileId,
        options: {
          ...options,
          min_quality: minQuality ? Number(minQuality) : undefined,
        },
      },
      { onSuccess: (result) => setJobId(result.job_id) }
    );
  };

  const progress =
    job && job.total_variants > 0
      ? Math.round(((job.completed + job.failed) / job.total_variants) * 100)
      : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary-600" />
            <h2 className="text-lg font-semibold">Annotate with AlphaGenome Atlas</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 px-6 py-4">
          <p className="text-sm text-gray-600">
            Fetch precomputed AVI impact scores and feature attributions for every SNV in
            a loaded VCF. Indels and structural variants are skipped (Atlas covers SNVs
            only).
          </p>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">VCF file</label>
            <select
              value={effectiveFileId ?? ''}
              onChange={(e) => setVcfFileId(Number(e.target.value))}
              disabled={isRunning}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            >
              {files.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.filename} ({f.total_variants.toLocaleString()} variants)
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2">
              <input
                type="checkbox"
                checked={options.non_ref_only ?? true}
                disabled={isRunning}
                onChange={(e) => setOptions((o) => ({ ...o, non_ref_only: e.target.checked }))}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">Non-ref genotypes only</span>
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2">
              <input
                type="checkbox"
                checked={options.pass_only ?? true}
                disabled={isRunning}
                onChange={(e) => setOptions((o) => ({ ...o, pass_only: e.target.checked }))}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">PASS filter only</span>
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2">
              <input
                type="checkbox"
                checked={options.coding_only ?? false}
                disabled={isRunning}
                onChange={(e) => setOptions((o) => ({ ...o, coding_only: e.target.checked }))}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">Coding only</span>
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2">
              <input
                type="checkbox"
                checked={options.overwrite ?? false}
                disabled={isRunning}
                onChange={(e) => setOptions((o) => ({ ...o, overwrite: e.target.checked }))}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">Re-annotate existing</span>
            </label>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Minimum quality (optional)
            </label>
            <input
              type="number"
              value={minQuality}
              disabled={isRunning}
              onChange={(e) => setMinQuality(e.target.value)}
              placeholder="e.g. 30"
              className="w-32 rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>

          {startMutation.isError && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {(startMutation.error as { response?: { data?: { detail?: string } } })?.response
                ?.data?.detail ?? 'Failed to start annotation job'}
            </div>
          )}

          {job && (
            <div className="rounded-lg border border-gray-200 p-4">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 font-medium">
                  {job.status === 'completed' ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : job.status === 'failed' ? (
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                  ) : (
                    <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
                  )}
                  {job.status === 'completed'
                    ? 'Annotation complete'
                    : job.status === 'failed'
                      ? 'Job failed'
                      : 'Annotating...'}
                </span>
                <span className="text-gray-500">{progress}%</span>
              </div>
              <div className="mb-3 h-2 overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full bg-primary-600 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600">
                <span>Annotated: {job.completed.toLocaleString()}</span>
                <span>Failed: {job.failed.toLocaleString()}</span>
                <span>Skipped (non-SNV): {job.skipped_non_snv.toLocaleString()}</span>
                <span>Skipped (existing): {job.skipped_existing.toLocaleString()}</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            {job?.status === 'completed' ? 'Done' : 'Close'}
          </button>
          <button
            onClick={handleStart}
            disabled={!effectiveFileId || isRunning || startMutation.isPending}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {isRunning ? 'Running...' : 'Start annotation'}
          </button>
        </div>
      </div>
    </div>
  );
}
