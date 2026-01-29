import { useState } from 'react';
import { Link } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Loader2,
  Search,
  Filter,
  ShieldAlert,
  ShieldCheck,
  Shield,
} from 'lucide-react';
import Header from '../components/layout/Header';
import { useDiseaseRiskPanel, useLoadedFiles } from '../hooks/useApi';
import type { DiseaseRiskVariant } from '../types';

const SIGNIFICANCE_COLORS: Record<string, string> = {
  pathogenic: 'bg-red-100 text-red-800 border-red-200',
  'likely pathogenic': 'bg-orange-100 text-orange-800 border-orange-200',
  'likely_pathogenic': 'bg-orange-100 text-orange-800 border-orange-200',
  'uncertain significance': 'bg-yellow-100 text-yellow-800 border-yellow-200',
  'likely benign': 'bg-green-100 text-green-800 border-green-200',
  'likely_benign': 'bg-green-100 text-green-800 border-green-200',
  benign: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  'risk factor': 'bg-amber-100 text-amber-800 border-amber-200',
  'risk_factor': 'bg-amber-100 text-amber-800 border-amber-200',
};

const RISK_CATEGORY_COLORS: Record<string, string> = {
  high: 'text-red-600 bg-red-100',
  moderate: 'text-amber-600 bg-amber-100',
  low: 'text-blue-600 bg-blue-100',
  unknown: 'text-gray-600 bg-gray-100',
};

export default function DiseaseRisk() {
  const { data: filesData } = useLoadedFiles();
  const [selectedFileId, setSelectedFileId] = useState<number | undefined>();
  const { data: panel, isLoading, error } = useDiseaseRiskPanel(selectedFileId);
  const [expandedVariants, setExpandedVariants] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('');

  const toggleVariant = (variantId: number) => {
    setExpandedVariants((prev) => {
      const next = new Set(prev);
      if (next.has(variantId)) {
        next.delete(variantId);
      } else {
        next.add(variantId);
      }
      return next;
    });
  };

  // Combine all variants
  const allVariants = panel
    ? [
        ...(panel.pathogenic_variants || []),
        ...(panel.likely_pathogenic_variants || []),
        ...(panel.risk_factors || []),
      ]
    : [];

  // Filter variants
  const filteredVariants = allVariants.filter((v) => {
    const matchesSearch =
      !searchTerm ||
      v.variant.gene_symbol?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.disease_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.variant.rsid?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory =
      !filterCategory || v.risk_category === filterCategory;

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="flex-1 overflow-auto">
      <Header
        title="Disease Risk"
        subtitle="Pathogenic and risk-associated variants"
      />

      <div className="p-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4 mb-6">
          <div className="card border-l-4 border-l-red-500">
            <div className="card-body flex items-center gap-4">
              <div className="rounded-lg bg-red-100 p-3">
                <ShieldAlert className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Pathogenic</p>
                <p className="text-2xl font-semibold text-red-600">
                  {panel?.pathogenic_variants?.length ?? '-'}
                </p>
              </div>
            </div>
          </div>
          <div className="card border-l-4 border-l-orange-500">
            <div className="card-body flex items-center gap-4">
              <div className="rounded-lg bg-orange-100 p-3">
                <AlertTriangle className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Likely Pathogenic</p>
                <p className="text-2xl font-semibold text-orange-600">
                  {panel?.likely_pathogenic_variants?.length ?? '-'}
                </p>
              </div>
            </div>
          </div>
          <div className="card border-l-4 border-l-amber-500">
            <div className="card-body flex items-center gap-4">
              <div className="rounded-lg bg-amber-100 p-3">
                <Info className="h-6 w-6 text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Risk Factors</p>
                <p className="text-2xl font-semibold text-amber-600">
                  {panel?.risk_factors?.length ?? '-'}
                </p>
              </div>
            </div>
          </div>
          <div className="card border-l-4 border-l-blue-500">
            <div className="card-body flex items-center gap-4">
              <div className="rounded-lg bg-blue-100 p-3">
                <Shield className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Reviewed</p>
                <p className="text-2xl font-semibold text-blue-600">
                  {allVariants.length}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Important Notice */}
        <div className="card border-l-4 border-l-amber-500 mb-6">
          <div className="card-body">
            <div className="flex items-start gap-4">
              <AlertTriangle className="h-6 w-6 text-amber-500 flex-shrink-0" />
              <div>
                <h3 className="font-medium text-gray-900">Important Disclaimer</h3>
                <p className="mt-1 text-sm text-gray-600">
                  This information is provided for educational purposes only and should not be
                  used for medical diagnosis or treatment. Variant classifications may change
                  over time as new evidence emerges. Always consult with a qualified healthcare
                  provider or genetic counselor for interpretation of genetic results.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="card mb-6">
          <div className="card-body">
            <div className="flex flex-wrap gap-4">
              {/* File Selector */}
              {filesData && filesData.files.length > 1 && (
                <select
                  value={selectedFileId ?? ''}
                  onChange={(e) =>
                    setSelectedFileId(
                      e.target.value ? parseInt(e.target.value, 10) : undefined
                    )
                  }
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                >
                  <option value="">All Files</option>
                  {filesData.files.map((file) => (
                    <option key={file.id} value={file.id}>
                      {file.filename}
                    </option>
                  ))}
                </select>
              )}

              {/* Risk Category Filter */}
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                <option value="">All Risk Categories</option>
                <option value="high">High Risk</option>
                <option value="moderate">Moderate Risk</option>
                <option value="low">Low Risk</option>
              </select>

              {/* Search */}
              <div className="flex-1 min-w-[250px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search genes or diseases..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Summary Text */}
        {panel?.summary && (
          <div className="card mb-6">
            <div className="card-body">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
              <p className="text-sm text-gray-600">{panel.summary}</p>
            </div>
          </div>
        )}

        {/* Variant Cards */}
        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : error ? (
          <div className="card">
            <div className="card-body flex flex-col items-center justify-center py-12 text-red-500">
              <AlertCircle className="h-12 w-12 mb-2" />
              <p>Error loading disease risk data</p>
            </div>
          </div>
        ) : filteredVariants.length > 0 ? (
          <div className="space-y-4">
            {/* Group by significance */}
            {panel?.pathogenic_variants && panel.pathogenic_variants.length > 0 && (
              <VariantGroup
                title="Pathogenic Variants"
                icon={ShieldAlert}
                iconColor="text-red-600"
                bgColor="bg-red-100"
                variants={panel.pathogenic_variants.filter((v) =>
                  filteredVariants.some((fv) => fv.variant.id === v.variant.id)
                )}
                expandedVariants={expandedVariants}
                onToggleVariant={toggleVariant}
              />
            )}

            {panel?.likely_pathogenic_variants &&
              panel.likely_pathogenic_variants.length > 0 && (
                <VariantGroup
                  title="Likely Pathogenic Variants"
                  icon={AlertTriangle}
                  iconColor="text-orange-600"
                  bgColor="bg-orange-100"
                  variants={panel.likely_pathogenic_variants.filter((v) =>
                    filteredVariants.some((fv) => fv.variant.id === v.variant.id)
                  )}
                  expandedVariants={expandedVariants}
                  onToggleVariant={toggleVariant}
                />
              )}

            {panel?.risk_factors && panel.risk_factors.length > 0 && (
              <VariantGroup
                title="Risk Factors"
                icon={Info}
                iconColor="text-amber-600"
                bgColor="bg-amber-100"
                variants={panel.risk_factors.filter((v) =>
                  filteredVariants.some((fv) => fv.variant.id === v.variant.id)
                )}
                expandedVariants={expandedVariants}
                onToggleVariant={toggleVariant}
              />
            )}
          </div>
        ) : (
          <div className="card">
            <div className="card-body flex flex-col items-center justify-center py-12 text-gray-400">
              <ShieldCheck className="h-12 w-12 mb-2 text-emerald-400" />
              <p className="text-emerald-600 font-medium">
                No pathogenic variants found
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {allVariants.length === 0
                  ? 'Load VCF data to check for disease-associated variants'
                  : 'No variants match your current filters'}
              </p>
              {allVariants.length === 0 && (
                <Link
                  to="/files"
                  className="mt-4 text-sm text-primary-600 hover:underline"
                >
                  Load VCF data
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function VariantGroup({
  title,
  icon: Icon,
  iconColor,
  bgColor,
  variants,
  expandedVariants,
  onToggleVariant,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  bgColor: string;
  variants: DiseaseRiskVariant[];
  expandedVariants: Set<number>;
  onToggleVariant: (id: number) => void;
}) {
  if (variants.length === 0) return null;

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <div className={clsx('rounded-lg p-2', bgColor)}>
          <Icon className={clsx('h-5 w-5', iconColor)} />
        </div>
        <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-600">
          {variants.length}
        </span>
      </div>
      <div className="space-y-3">
        {variants.map((drv) => (
          <DiseaseVariantCard
            key={drv.variant.id}
            diseaseVariant={drv}
            expanded={expandedVariants.has(drv.variant.id)}
            onToggle={() => onToggleVariant(drv.variant.id)}
          />
        ))}
      </div>
    </div>
  );
}

function DiseaseVariantCard({
  diseaseVariant,
  expanded,
  onToggle,
}: {
  diseaseVariant: DiseaseRiskVariant;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { variant, disease_name, clinical_significance, inheritance, risk_category } =
    diseaseVariant;

  const sigClass =
    SIGNIFICANCE_COLORS[clinical_significance?.toLowerCase() || ''] ||
    'bg-gray-100 text-gray-600';

  return (
    <div className="card">
      <div
        className="card-header flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={onToggle}
      >
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h4 className="font-semibold text-gray-900">
              {variant.gene_symbol || 'Unknown Gene'}
            </h4>
            <span
              className={clsx(
                'rounded-full border px-2 py-0.5 text-xs font-medium capitalize',
                sigClass
              )}
            >
              {formatSignificance(clinical_significance)}
            </span>
            {risk_category && (
              <span
                className={clsx(
                  'rounded-full px-2 py-0.5 text-xs font-medium',
                  RISK_CATEGORY_COLORS[risk_category] || 'bg-gray-100 text-gray-600'
                )}
              >
                {risk_category.charAt(0).toUpperCase() + risk_category.slice(1)} Risk
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mt-1">{disease_name}</p>
          <p className="text-xs text-gray-400 font-mono mt-1">
            {variant.chromosome}:{variant.position.toLocaleString()}{' '}
            {variant.reference} {'>'} {variant.alternate}
            {variant.rsid && ` (${variant.rsid})`}
          </p>
        </div>

        <div className="flex items-center gap-4 ml-4">
          {inheritance && (
            <div className="text-right hidden sm:block">
              <p className="text-xs text-gray-500">Inheritance</p>
              <p className="text-sm font-medium text-gray-700">{inheritance}</p>
            </div>
          )}
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400 flex-shrink-0" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="card-body border-t border-gray-100">
          <div className="grid gap-4 sm:grid-cols-2">
            {/* Variant Details */}
            <div>
              <h5 className="text-sm font-medium text-gray-700 mb-3">
                Variant Details
              </h5>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Gene</dt>
                  <dd className="font-medium text-gray-900">
                    {variant.gene_symbol || '-'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">rsID</dt>
                  <dd>
                    {variant.rsid ? (
                      <a
                        href={`https://www.ncbi.nlm.nih.gov/snp/${variant.rsid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:underline"
                      >
                        {variant.rsid}
                      </a>
                    ) : (
                      '-'
                    )}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Genotype</dt>
                  <dd className="font-mono">{variant.genotype || '-'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Zygosity</dt>
                  <dd>{variant.zygosity || '-'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Consequence</dt>
                  <dd className="text-right max-w-[200px] truncate">
                    {variant.consequence?.replace(/_/g, ' ') || '-'}
                  </dd>
                </div>
                {variant.protein_change && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Protein Change</dt>
                    <dd className="font-mono">{variant.protein_change}</dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Disease Details */}
            <div>
              <h5 className="text-sm font-medium text-gray-700 mb-3">
                Disease Association
              </h5>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Disease</dt>
                  <dd className="font-medium text-gray-900 text-right max-w-[200px]">
                    {disease_name}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Classification</dt>
                  <dd className="capitalize">
                    {formatSignificance(clinical_significance)}
                  </dd>
                </div>
                {inheritance && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Inheritance</dt>
                    <dd>{inheritance}</dd>
                  </div>
                )}
                {diseaseVariant.disease_id && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Disease ID</dt>
                    <dd className="font-mono text-xs">
                      {diseaseVariant.disease_id}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap gap-3">
            <Link
              to={`/analysis/${variant.id}`}
              className="btn btn-primary text-sm"
            >
              Analyze with AlphaGenome
            </Link>
            {variant.rsid && (
              <>
                <a
                  href={`https://www.ncbi.nlm.nih.gov/clinvar/?term=${variant.rsid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary text-sm inline-flex items-center gap-2"
                >
                  View in ClinVar
                  <ExternalLink className="h-4 w-4" />
                </a>
                <a
                  href={`https://www.ncbi.nlm.nih.gov/snp/${variant.rsid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary text-sm inline-flex items-center gap-2"
                >
                  View in dbSNP
                  <ExternalLink className="h-4 w-4" />
                </a>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatSignificance(significance: string | null | undefined): string {
  if (!significance) return '-';
  return significance
    .replace(/_/g, ' ')
    .replace(/\//g, ' / ')
    .toLowerCase();
}
