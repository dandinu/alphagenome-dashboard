import { useState } from 'react';
import { Link } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  Pill,
  AlertCircle,
  CheckCircle,
  Info,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Dna,
  Loader2,
  Search,
} from 'lucide-react';
import Header from '../components/layout/Header';
import { usePharmacogenomicsPanel, useLoadedFiles } from '../hooks/useApi';
import type { PharmaGeneReport, DrugAssociation, Variant } from '../types';

const EVIDENCE_COLORS: Record<string, string> = {
  '1A': 'bg-red-100 text-red-800 border-red-200',
  '1B': 'bg-orange-100 text-orange-800 border-orange-200',
  '2A': 'bg-amber-100 text-amber-800 border-amber-200',
  '2B': 'bg-yellow-100 text-yellow-800 border-yellow-200',
  '3': 'bg-blue-100 text-blue-800 border-blue-200',
  '4': 'bg-gray-100 text-gray-600 border-gray-200',
};

const EVIDENCE_DESCRIPTIONS: Record<string, string> = {
  '1A': 'Annotation is for a variant-drug combination in a CPIC or Dutch guideline',
  '1B': 'Annotation for a variant-drug combination where the preponderance of evidence shows an association',
  '2A': 'Annotation for a variant-drug combination with moderate evidence',
  '2B': 'Annotation for a variant-drug combination with limited evidence',
  '3': 'Annotation based on single significant study',
  '4': 'Case reports, non-significant studies',
};

export default function Pharmacogenomics() {
  const { data: filesData } = useLoadedFiles();
  const [selectedFileId, setSelectedFileId] = useState<number | undefined>();
  const { data: panel, isLoading, error } = usePharmacogenomicsPanel(selectedFileId);
  const [expandedGenes, setExpandedGenes] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');

  const toggleGene = (gene: string) => {
    setExpandedGenes((prev) => {
      const next = new Set(prev);
      if (next.has(gene)) {
        next.delete(gene);
      } else {
        next.add(gene);
      }
      return next;
    });
  };

  const filteredGenes = panel?.genes.filter(
    (gene) =>
      gene.gene_symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      gene.gene_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      gene.drugs.some((d) =>
        d.drug_name.toLowerCase().includes(searchTerm.toLowerCase())
      )
  );

  return (
    <div className="flex-1 overflow-auto">
      <Header
        title="Pharmacogenomics"
        subtitle="Drug-gene interactions and recommendations"
      />

      <div className="p-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3 mb-6">
          <div className="card">
            <div className="card-body flex items-center gap-4">
              <div className="rounded-lg bg-purple-100 p-3">
                <Pill className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Actionable Variants</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {panel?.total_actionable_variants ?? '-'}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-body flex items-center gap-4">
              <div className="rounded-lg bg-blue-100 p-3">
                <Dna className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Pharmacogenes</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {panel?.genes.length ?? '-'}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-body flex items-center gap-4">
              <div className="rounded-lg bg-amber-100 p-3">
                <AlertCircle className="h-6 w-6 text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">High Evidence</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {panel?.genes.filter((g) =>
                    g.drugs.some((d) => d.highest_evidence?.startsWith('1'))
                  ).length ?? '-'}
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

              {/* Search */}
              <div className="flex-1 min-w-[250px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search genes or drugs..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Evidence Legend */}
        <div className="card mb-6">
          <div className="card-body">
            <h4 className="text-sm font-medium text-gray-700 mb-3">
              Evidence Level Legend (PharmGKB)
            </h4>
            <div className="flex flex-wrap gap-3">
              {Object.entries(EVIDENCE_COLORS).map(([level, colors]) => (
                <div
                  key={level}
                  className="group relative"
                >
                  <span
                    className={clsx(
                      'inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium',
                      colors
                    )}
                  >
                    Level {level}
                  </span>
                  <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block z-10 w-64 rounded-lg bg-gray-900 p-2 text-xs text-white shadow-lg">
                    {EVIDENCE_DESCRIPTIONS[level]}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Gene Cards */}
        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : error ? (
          <div className="card">
            <div className="card-body flex flex-col items-center justify-center py-12 text-red-500">
              <AlertCircle className="h-12 w-12 mb-2" />
              <p>Error loading pharmacogenomics data</p>
            </div>
          </div>
        ) : filteredGenes && filteredGenes.length > 0 ? (
          <div className="space-y-4">
            {filteredGenes.map((gene) => (
              <GeneCard
                key={gene.gene_symbol}
                gene={gene}
                expanded={expandedGenes.has(gene.gene_symbol)}
                onToggle={() => toggleGene(gene.gene_symbol)}
              />
            ))}
          </div>
        ) : (
          <div className="card">
            <div className="card-body flex flex-col items-center justify-center py-12 text-gray-400">
              <Pill className="h-12 w-12 mb-2" />
              <p>No pharmacogenomic variants found</p>
              {!panel?.genes.length && (
                <Link
                  to="/files"
                  className="mt-2 text-sm text-primary-600 hover:underline"
                >
                  Load VCF data to get started
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function GeneCard({
  gene,
  expanded,
  onToggle,
}: {
  gene: PharmaGeneReport;
  expanded: boolean;
  onToggle: () => void;
}) {
  const highestEvidence = gene.drugs.reduce(
    (acc, d) => {
      if (!d.highest_evidence) return acc;
      if (!acc || d.highest_evidence < acc) return d.highest_evidence;
      return acc;
    },
    null as string | null
  );

  return (
    <div className="card">
      <div
        className="card-header flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={onToggle}
      >
        <div className="flex items-center gap-4">
          <div className="rounded-lg bg-purple-100 p-2">
            <Dna className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-gray-900">{gene.gene_symbol}</h4>
              {highestEvidence && (
                <span
                  className={clsx(
                    'rounded-full border px-2 py-0.5 text-xs font-medium',
                    EVIDENCE_COLORS[highestEvidence] ?? 'bg-gray-100 text-gray-600'
                  )}
                >
                  Level {highestEvidence}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500">{gene.gene_name}</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm font-medium text-gray-900">
              {gene.variants.length} variant{gene.variants.length !== 1 ? 's' : ''}
            </p>
            <p className="text-xs text-gray-500">
              {gene.drugs.length} drug{gene.drugs.length !== 1 ? 's' : ''}
            </p>
          </div>
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="card-body border-t border-gray-100">
          {/* Phenotype Info */}
          {(gene.diplotype || gene.phenotype) && (
            <div className="mb-4 rounded-lg bg-purple-50 p-4">
              <div className="flex flex-wrap gap-6">
                {gene.diplotype && (
                  <div>
                    <p className="text-xs text-purple-600 font-medium">Diplotype</p>
                    <p className="text-sm font-mono text-purple-900">
                      {gene.diplotype}
                    </p>
                  </div>
                )}
                {gene.phenotype && (
                  <div>
                    <p className="text-xs text-purple-600 font-medium">Phenotype</p>
                    <p className="text-sm text-purple-900">{gene.phenotype}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {gene.recommendations.length > 0 && (
            <div className="mb-4">
              <h5 className="text-sm font-medium text-gray-700 mb-2">
                Recommendations
              </h5>
              <div className="space-y-2">
                {gene.recommendations.map((rec, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 rounded-lg bg-amber-50 p-3"
                  >
                    <Info className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-amber-900">{rec}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Variants */}
          <div className="mb-4">
            <h5 className="text-sm font-medium text-gray-700 mb-2">
              Your Variants
            </h5>
            <div className="overflow-x-auto">
              <table className="data-table text-sm">
                <thead>
                  <tr>
                    <th>rsID</th>
                    <th>Location</th>
                    <th>Change</th>
                    <th>Genotype</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {gene.variants.map((variant) => (
                    <tr key={variant.id}>
                      <td>
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
                      </td>
                      <td className="font-mono">
                        {variant.chromosome}:{variant.position.toLocaleString()}
                      </td>
                      <td className="font-mono">
                        {variant.reference} {'>'} {variant.alternate}
                      </td>
                      <td className="font-mono">{variant.genotype ?? '-'}</td>
                      <td>
                        <Link
                          to={`/analysis/${variant.id}`}
                          className="text-primary-600 hover:underline text-xs"
                        >
                          Analyze
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Drug Associations */}
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">
              Drug Associations
            </h5>
            <div className="grid gap-3 sm:grid-cols-2">
              {gene.drugs.map((drug) => (
                <DrugCard key={drug.drug_id || drug.drug_name} drug={drug} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DrugCard({ drug }: { drug: DrugAssociation }) {
  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-2">
        <h6 className="font-medium text-gray-900">{drug.drug_name}</h6>
        {drug.highest_evidence && (
          <span
            className={clsx(
              'rounded-full border px-2 py-0.5 text-xs font-medium',
              EVIDENCE_COLORS[drug.highest_evidence] ?? 'bg-gray-100 text-gray-600'
            )}
          >
            {drug.highest_evidence}
          </span>
        )}
      </div>
      {drug.drug_id && (
        <a
          href={`https://www.pharmgkb.org/chemical/${drug.drug_id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-primary-600 hover:underline"
        >
          View on PharmGKB
          <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}
