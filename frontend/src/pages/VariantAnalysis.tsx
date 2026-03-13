import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import {
  ArrowLeft,
  Play,
  Loader2,
  ExternalLink,
  Dna,
  Activity,
  Scissors,
  Brain,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Layers,
  Target,
  Box,
  Grid3X3,
  Zap,
} from 'lucide-react';
import Header from '../components/layout/Header';
import {
  useVariant,
  useVariantAnalysis,
  useScoreVariant,
  useOutputTypes,
  useVariants,
  useFullAnalysis,
} from '../hooks/useApi';
import type { AnalysisResult } from '../types';

const IMPACT_COLORS: Record<string, string> = {
  HIGH: 'bg-red-100 text-red-800 border-red-200',
  MODERATE: 'bg-amber-100 text-amber-800 border-amber-200',
  LOW: 'bg-blue-100 text-blue-800 border-blue-200',
  MODIFIER: 'bg-gray-100 text-gray-600 border-gray-200',
};

export default function VariantAnalysis() {
  const { variantId } = useParams<{ variantId: string }>();

  const parsedVariantId = variantId ? parseInt(variantId, 10) : null;

  if (!parsedVariantId) {
    return <VariantSelector />;
  }

  return <VariantAnalysisDetail variantId={parsedVariantId} />;
}

function VariantSelector() {
  const [searchTerm, setSearchTerm] = useState('');
  const { data, isLoading } = useVariants(1, 20, {
    search: searchTerm || undefined,
    is_coding: true,
  });

  return (
    <div className="flex-1 overflow-auto">
      <Header
        title="Variant Analysis"
        subtitle="Select a variant to analyze with AlphaGenome"
      />

      <div className="p-6">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Select Variant</h3>
          </div>
          <div className="card-body">
            <div className="mb-4">
              <input
                type="text"
                placeholder="Search by gene, rsID, or position..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>

            {isLoading ? (
              <div className="flex h-48 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            ) : data && data.variants.length > 0 ? (
              <div className="space-y-2">
                {data.variants.map((variant) => (
                  <Link
                    key={variant.id}
                    to={`/analysis/${variant.id}`}
                    className="flex items-center justify-between rounded-lg border border-gray-200 p-4 hover:border-primary-300 hover:bg-primary-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="rounded-lg bg-primary-100 p-2">
                        <Dna className="h-5 w-5 text-primary-600" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">
                            {variant.gene_symbol || 'Unknown Gene'}
                          </span>
                          {variant.rsid && (
                            <span className="text-sm text-primary-600">
                              {variant.rsid}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500">
                          {variant.chromosome}:{variant.position.toLocaleString()}{' '}
                          <span className="font-mono">
                            {variant.reference} {'>'} {variant.alternate}
                          </span>
                          {variant.protein_change && (
                            <span className="ml-2 text-gray-400">
                              ({variant.protein_change})
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    {variant.impact && (
                      <span
                        className={clsx(
                          'rounded-full px-3 py-1 text-xs font-medium',
                          IMPACT_COLORS[variant.impact] ?? 'bg-gray-100 text-gray-600'
                        )}
                      >
                        {variant.impact}
                      </span>
                    )}
                  </Link>
                ))}
              </div>
            ) : (
              <div className="flex h-48 flex-col items-center justify-center text-gray-400">
                <Dna className="h-12 w-12 mb-2" />
                <p>No variants found</p>
                <Link
                  to="/files"
                  className="mt-2 text-sm text-primary-600 hover:underline"
                >
                  Load VCF data first
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function VariantAnalysisDetail({ variantId }: { variantId: number }) {
  const navigate = useNavigate();
  const { data: variant, isLoading: variantLoading } = useVariant(variantId);
  const { data: analysis, isLoading: analysisLoading, refetch } = useVariantAnalysis(variantId);
  const { data: outputTypes } = useOutputTypes();
  const scoreVariant = useScoreVariant();
  const fullAnalysis = useFullAnalysis();

  const [selectedTypes, setSelectedTypes] = useState<string[]>([
    'RNA_SEQ',
    'SPLICE_SITES',
    'ATAC',
  ]);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  const handleRunAnalysis = () => {
    scoreVariant.mutate(
      { variantId, analysisTypes: selectedTypes },
      { onSuccess: () => refetch() }
    );
  };

  const handleFullAnalysis = () => {
    fullAnalysis.mutate(
      { variantId },
      { onSuccess: () => refetch() }
    );
  };

  const toggleExpanded = (type: string) => {
    setExpandedResults((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  if (variantLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!variant) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <p className="text-gray-600">Variant not found</p>
        <button
          onClick={() => navigate('/analysis')}
          className="mt-4 text-primary-600 hover:underline"
        >
          Select another variant
        </button>
      </div>
    );
  }

  const isRunning = scoreVariant.isPending || fullAnalysis.isPending;

  return (
    <div className="flex-1 overflow-auto">
      <Header
        title="Variant Analysis"
        subtitle={`${variant.gene_symbol || 'Unknown'} - ${variant.chromosome}:${variant.position.toLocaleString()}`}
      />

      <div className="p-6">
        {/* Back Button */}
        <button
          onClick={() => navigate('/analysis')}
          className="mb-4 flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Select different variant
        </button>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Variant Info Card */}
          <div className="card lg:col-span-1">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">Variant Details</h3>
            </div>
            <div className="card-body space-y-4">
              <VariantInfoRow label="Gene" value={variant.gene_symbol} />
              <VariantInfoRow label="rsID" value={variant.rsid} link={variant.rsid ? `https://www.ncbi.nlm.nih.gov/snp/${variant.rsid}` : undefined} />
              <VariantInfoRow
                label="Location"
                value={`${variant.chromosome}:${variant.position.toLocaleString()}`}
              />
              <VariantInfoRow
                label="Change"
                value={`${variant.reference} > ${variant.alternate}`}
                mono
              />
              <VariantInfoRow label="Protein Change" value={variant.protein_change} mono />
              <VariantInfoRow label="Consequence" value={variant.consequence?.replace(/_/g, ' ')} />
              <VariantInfoRow label="Genotype" value={variant.genotype} mono />
              <VariantInfoRow label="Zygosity" value={variant.zygosity} />
              {variant.impact && (
                <div className="pt-2">
                  <span
                    className={clsx(
                      'inline-flex rounded-full px-3 py-1 text-sm font-medium border',
                      IMPACT_COLORS[variant.impact] ?? 'bg-gray-100 text-gray-600'
                    )}
                  >
                    {variant.impact} Impact
                  </span>
                </div>
              )}

              {/* ClinVar Badge */}
              {variant.clinvar && (
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-xs text-gray-500 mb-1">ClinVar Classification</p>
                  <span
                    className={clsx(
                      'inline-flex rounded-full px-3 py-1 text-sm font-medium',
                      getClinVarClass(variant.clinvar.clinical_significance)
                    )}
                  >
                    {formatClinVar(variant.clinvar.clinical_significance)}
                  </span>
                  {variant.clinvar.disease_names && (
                    <p className="mt-2 text-sm text-gray-600">
                      {variant.clinvar.disease_names}
                    </p>
                  )}
                </div>
              )}

              {/* Composite Splicing Score */}
              {analysis?.composite_splicing_score != null && (
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-xs text-gray-500 mb-1">Composite Splicing Score</p>
                  <p className={clsx(
                    'text-2xl font-bold',
                    getScoreColor(analysis.composite_splicing_score)
                  )}>
                    {analysis.composite_splicing_score.toFixed(3)}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Analysis Panel */}
          <div className="lg:col-span-2 space-y-6">
            {/* Run Analysis Card */}
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">
                  AlphaGenome Analysis
                </h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleFullAnalysis}
                    disabled={isRunning}
                    className="btn bg-purple-600 text-white hover:bg-purple-700 flex items-center gap-2"
                  >
                    {fullAnalysis.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Zap className="h-4 w-4" />
                        Full Analysis
                      </>
                    )}
                  </button>
                  <button
                    onClick={handleRunAnalysis}
                    disabled={isRunning || selectedTypes.length === 0}
                    className="btn btn-primary flex items-center gap-2"
                  >
                    {scoreVariant.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        Run Selected
                      </>
                    )}
                  </button>
                </div>
              </div>
              <div className="card-body">
                <p className="text-sm text-gray-600 mb-4">
                  Select analysis types or run Full Analysis for all capabilities:
                </p>
                <div className="flex flex-wrap gap-2">
                  {getAnalysisTypeButtons(outputTypes?.output_types).map(
                    ({ type, icon: Icon, label }) => (
                      <button
                        key={type}
                        onClick={() => {
                          setSelectedTypes((prev) =>
                            prev.includes(type)
                              ? prev.filter((t) => t !== type)
                              : [...prev, type]
                          );
                        }}
                        className={clsx(
                          'rounded-full px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5',
                          selectedTypes.includes(type)
                            ? 'bg-primary-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        )}
                      >
                        <Icon className="h-3.5 w-3.5" />
                        {label}
                      </button>
                    )
                  )}
                </div>
              </div>
            </div>

            {/* Server-generated Plots */}
            {analysis?.plots && Object.keys(analysis.plots).length > 0 && (
              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-medium text-gray-900">Generated Plots</h3>
                </div>
                <div className="card-body space-y-4">
                  {Object.entries(analysis.plots).map(([type, url]) => (
                    <div key={type}>
                      <h5 className="text-sm font-medium text-gray-700 mb-2">
                        {type.replace(/_/g, ' ')}
                      </h5>
                      <img
                        src={url}
                        alt={`${type} plot`}
                        className="w-full rounded-lg border border-gray-200"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Results */}
            {analysisLoading ? (
              <div className="card">
                <div className="card-body flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                </div>
              </div>
            ) : analysis && analysis.analyses.length > 0 ? (
              <div className="space-y-4">
                {analysis.analyses.map((result) => (
                  <AnalysisResultCard
                    key={result.id}
                    result={result}
                    variantId={variantId}
                    expanded={expandedResults.has(result.analysis_type)}
                    onToggle={() => toggleExpanded(result.analysis_type)}
                    plotUrl={analysis.plots?.[result.analysis_type] ?? null}
                  />
                ))}
              </div>
            ) : (
              <div className="card">
                <div className="card-body flex flex-col items-center justify-center py-12 text-gray-400">
                  <Brain className="h-12 w-12 mb-2" />
                  <p>No analysis results yet</p>
                  <p className="text-sm">
                    Click "Full Analysis" or "Run Selected" to analyze this variant
                  </p>
                </div>
              </div>
            )}

            {/* Epigenomic Summary Cards */}
            {analysis && (analysis.histone_impact || analysis.tf_binding_impact || analysis.contact_map_impact) && (
              <div className="grid gap-4 sm:grid-cols-3">
                {analysis.histone_impact && (
                  <EpigenomicSummaryCard
                    title="Histone Marks"
                    icon={Layers}
                    data={analysis.histone_impact as Record<string, unknown>}
                  />
                )}
                {analysis.tf_binding_impact && (
                  <EpigenomicSummaryCard
                    title="TF Binding"
                    icon={Target}
                    data={analysis.tf_binding_impact as Record<string, unknown>}
                  />
                )}
                {analysis.contact_map_impact && (
                  <EpigenomicSummaryCard
                    title="3D Contacts"
                    icon={Box}
                    data={analysis.contact_map_impact as Record<string, unknown>}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function EpigenomicSummaryCard({
  title,
  icon: Icon,
  data,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  data: Record<string, unknown>;
}) {
  const summary = (data as Record<string, Record<string, unknown>>)?.summary ?? {};
  const maxChange = typeof summary.max_change === 'number' ? summary.max_change : null;

  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center gap-2 mb-3">
          <div className="rounded-lg bg-indigo-100 p-2">
            <Icon className="h-4 w-4 text-indigo-600" />
          </div>
          <h4 className="font-medium text-gray-900 text-sm">{title}</h4>
        </div>
        {maxChange !== null && (
          <div>
            <p className="text-xs text-gray-500">Max Change</p>
            <p className={clsx('text-lg font-semibold', getScoreColor(maxChange))}>
              {maxChange.toFixed(4)}
            </p>
          </div>
        )}
        {typeof summary.n_tracks_affected === 'number' && (
          <p className="text-xs text-gray-500 mt-1">
            {String(summary.n_tracks_affected)} / {String(summary.n_tracks_total ?? '?')} tracks affected
          </p>
        )}
        {typeof summary.n_tfs_affected === 'number' && (
          <p className="text-xs text-gray-500 mt-1">
            {summary.n_tfs_affected} TFs affected
          </p>
        )}
      </div>
    </div>
  );
}

function VariantInfoRow({
  label,
  value,
  mono = false,
  link,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
  link?: string;
}) {
  return (
    <div className="flex justify-between">
      <span className="text-sm text-gray-500">{label}</span>
      {value ? (
        link ? (
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className={clsx(
              'text-sm text-primary-600 hover:underline flex items-center gap-1',
              mono && 'font-mono'
            )}
          >
            {value}
            <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <span className={clsx('text-sm text-gray-900', mono && 'font-mono')}>
            {value}
          </span>
        )
      ) : (
        <span className="text-sm text-gray-400">-</span>
      )}
    </div>
  );
}

function AnalysisResultCard({
  result,
  expanded,
  onToggle,
  plotUrl,
}: {
  result: AnalysisResult;
  variantId: number;
  expanded: boolean;
  onToggle: () => void;
  plotUrl: string | null;
}) {
  const Icon = getAnalysisIcon(result.analysis_type);

  // plot_data from the backend is {} when no server-side plot was generated;
  // fall back to mock data for the client-side Recharts visualisation.
  const plotData = (Array.isArray(result.plot_data) && result.plot_data.length > 0)
    ? result.plot_data
    : generateMockPlotData(result.analysis_type);

  return (
    <div className="card">
      <div
        className="card-header flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary-100 p-2">
            <Icon className="h-5 w-5 text-primary-600" />
          </div>
          <div>
            <h4 className="font-medium text-gray-900">
              {result.analysis_type.replace(/_/g, ' ')}
            </h4>
            <p className="text-sm text-gray-500">
              Analyzed {new Date(result.analyzed_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {result.score !== null && (
            <div className="text-right">
              <p className="text-xs text-gray-500">Score</p>
              <p className={clsx(
                'text-lg font-semibold',
                getScoreColor(result.score)
              )}>
                {result.score.toFixed(3)}
              </p>
            </div>
          )}
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="card-body border-t border-gray-100">
          {/* Score Details */}
          {result.score_details && Object.keys(result.score_details).length > 0 && (
            <div className="mb-6">
              <h5 className="text-sm font-medium text-gray-700 mb-3">Score Details</h5>
              <div className="space-y-4">
                {Object.entries(result.score_details).map(([key, value]) => {
                  // Nested scorer object like {mean, max, min, std, n_tracks}
                  if (value && typeof value === 'object' && !Array.isArray(value)) {
                    const obj = value as Record<string, unknown>;
                    // Skip "tidy" arrays from scorer data
                    const displayEntries = Object.entries(obj).filter(
                      ([k]) => k !== 'tidy'
                    );
                    if (displayEntries.length === 0) return null;
                    return (
                      <div key={key}>
                        <p className="text-xs font-medium text-gray-500 capitalize mb-2">
                          {key.replace(/_/g, ' ')}
                        </p>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                          {displayEntries.map(([k, v]) => (
                            <div key={k} className="rounded-lg bg-gray-50 p-3">
                              <p className="text-xs text-gray-500 capitalize">
                                {k.replace(/_/g, ' ')}
                              </p>
                              <p className="text-base font-semibold text-gray-900">
                                {typeof v === 'number'
                                  ? Math.abs(v) < 0.001 && v !== 0
                                    ? v.toExponential(2)
                                    : v.toFixed(4)
                                  : String(v ?? '-')}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  }
                  // Simple key-value
                  return (
                    <div key={key} className="rounded-lg bg-gray-50 p-3 inline-block mr-3">
                      <p className="text-xs text-gray-500 capitalize">
                        {key.replace(/_/g, ' ')}
                      </p>
                      <p className="text-base font-semibold text-gray-900">
                        {typeof value === 'number'
                          ? Math.abs(value) < 0.001 && value !== 0
                            ? value.toExponential(2)
                            : value.toFixed(4)
                          : String(value ?? '-')}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Server-generated plot (preferred) */}
          {plotUrl ? (
            <div>
              <h5 className="text-sm font-medium text-gray-700 mb-3">
                AlphaGenome Plot
              </h5>
              <img
                src={plotUrl}
                alt={`${result.analysis_type} plot`}
                className="w-full rounded-lg border border-gray-200"
              />
            </div>
          ) : (
            /* Fallback: client-side chart */
            <div>
              <h5 className="text-sm font-medium text-gray-700 mb-3">
                Prediction Track
              </h5>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {result.analysis_type.includes('SPLICE') ? (
                    <BarChart data={plotData as Record<string, unknown>[]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="position" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Bar dataKey="reference" fill="#10b981" name="Reference" />
                      <Bar dataKey="alternate" fill="#ef4444" name="Alternate" />
                    </BarChart>
                  ) : (
                    <LineChart data={plotData as Record<string, unknown>[]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="position" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="reference"
                        stroke="#10b981"
                        strokeWidth={2}
                        name="Reference"
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="alternate"
                        stroke="#ef4444"
                        strokeWidth={2}
                        name="Alternate"
                        dot={false}
                      />
                    </LineChart>
                  )}
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex items-center justify-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded bg-emerald-500" />
                  <span className="text-gray-600">Reference</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded bg-red-500" />
                  <span className="text-gray-600">Alternate</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ #
// Helpers
// ------------------------------------------------------------------ #

function getAnalysisTypeButtons(_outputTypes?: Record<string, string> | string[]) {
  const types = [
    { type: 'RNA_SEQ', icon: Activity, label: 'RNA-seq' },
    { type: 'SPLICE_SITES', icon: Scissors, label: 'Splice Sites' },
    { type: 'ATAC', icon: Dna, label: 'ATAC-seq' },
    { type: 'DNASE', icon: Dna, label: 'DNase-seq' },
    { type: 'CAGE', icon: Activity, label: 'CAGE' },
    { type: 'CHIP_HISTONE', icon: Layers, label: 'Histone Marks' },
    { type: 'CHIP_TF', icon: Target, label: 'TF Binding' },
    { type: 'CONTACT_MAPS', icon: Box, label: '3D Contacts' },
    { type: 'SPLICE_JUNCTIONS', icon: Scissors, label: 'Splice Junctions' },
    { type: 'SPLICE_SITE_USAGE', icon: Scissors, label: 'Splice Usage' },
    { type: 'PROCAP', icon: Activity, label: 'PRO-CAP' },
  ];
  return types;
}

function getAnalysisIcon(type: string) {
  if (type.includes('RNA') || type.includes('CAGE') || type.includes('PROCAP')) return Activity;
  if (type.includes('SPLICE')) return Scissors;
  if (type.includes('ATAC') || type.includes('DNASE')) return Dna;
  if (type.includes('HISTONE')) return Layers;
  if (type.includes('TF')) return Target;
  if (type.includes('CONTACT')) return Box;
  if (type === 'ISM') return Grid3X3;
  return Brain;
}

function getScoreColor(score: number): string {
  if (Math.abs(score) > 0.5) return 'text-red-600';
  if (Math.abs(score) > 0.2) return 'text-amber-600';
  return 'text-emerald-600';
}

function generateMockPlotData(type: string) {
  const data = [];
  for (let i = -50; i <= 50; i += 5) {
    data.push({
      position: i,
      reference: Math.random() * 0.5 + (type.includes('SPLICE') ? 0.3 : 0.2),
      alternate:
        Math.random() * 0.5 +
        (type.includes('SPLICE') ? 0.3 : 0.2) +
        (Math.abs(i) < 10 ? 0.2 : 0),
    });
  }
  return data;
}

function getClinVarClass(significance: string | null | undefined): string {
  if (!significance) return 'bg-gray-100 text-gray-600';
  const sig = significance.toLowerCase();
  if (sig.includes('pathogenic') && !sig.includes('likely'))
    return 'bg-red-100 text-red-800';
  if (sig.includes('likely_pathogenic') || sig.includes('likely pathogenic'))
    return 'bg-orange-100 text-orange-800';
  if (sig.includes('uncertain') || sig.includes('vus'))
    return 'bg-yellow-100 text-yellow-800';
  if (sig.includes('likely_benign') || sig.includes('likely benign'))
    return 'bg-green-100 text-green-800';
  if (sig.includes('benign')) return 'bg-emerald-100 text-emerald-800';
  return 'bg-gray-100 text-gray-600';
}

function formatClinVar(significance: string | null | undefined): string {
  if (!significance) return '-';
  return significance
    .replace(/_/g, ' ')
    .replace(/\//g, ' / ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}
