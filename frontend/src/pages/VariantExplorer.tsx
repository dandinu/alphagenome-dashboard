import { useState } from 'react';
import { Link } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  ChevronLeft,
  ChevronRight,
  Search,
  Filter,
  ExternalLink,
  Microscope,
} from 'lucide-react';
import Header from '../components/layout/Header';
import { useVariants } from '../hooks/useApi';
import type { Variant, VariantFilters } from '../types';

const IMPACT_COLORS: Record<string, string> = {
  HIGH: 'bg-red-100 text-red-800',
  MODERATE: 'bg-amber-100 text-amber-800',
  LOW: 'bg-blue-100 text-blue-800',
  MODIFIER: 'bg-gray-100 text-gray-600',
};

export default function VariantExplorer() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [filters, setFilters] = useState<VariantFilters>({});
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading, error } = useVariants(page, pageSize, {
    ...filters,
    search: searchTerm || undefined,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  const handleFilterChange = (key: keyof VariantFilters, value: string | boolean | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }));
    setPage(1);
  };

  return (
    <div className="flex-1 overflow-auto">
      <Header
        title="Variant Explorer"
        subtitle={`${data?.total.toLocaleString() ?? '...'} variants`}
      />

      <div className="p-6">
        {/* Search and Filters */}
        <div className="card mb-6">
          <div className="card-body">
            <div className="flex flex-wrap gap-4">
              {/* Search */}
              <form onSubmit={handleSearch} className="flex-1 min-w-[300px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by gene, rsID, or protein change..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </form>

              {/* Chromosome Filter */}
              <select
                value={filters.chromosome ?? ''}
                onChange={(e) => handleFilterChange('chromosome', e.target.value)}
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                <option value="">All Chromosomes</option>
                {Array.from({ length: 22 }, (_, i) => (
                  <option key={i + 1} value={String(i + 1)}>
                    Chr {i + 1}
                  </option>
                ))}
                <option value="X">Chr X</option>
                <option value="Y">Chr Y</option>
              </select>

              {/* Impact Filter */}
              <select
                value={filters.impact ?? ''}
                onChange={(e) => handleFilterChange('impact', e.target.value)}
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                <option value="">All Impacts</option>
                <option value="HIGH">High</option>
                <option value="MODERATE">Moderate</option>
                <option value="LOW">Low</option>
                <option value="MODIFIER">Modifier</option>
              </select>

              {/* Coding Only */}
              <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2">
                <input
                  type="checkbox"
                  checked={filters.is_coding ?? false}
                  onChange={(e) =>
                    handleFilterChange('is_coding', e.target.checked || undefined)
                  }
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">Coding only</span>
              </label>
            </div>
          </div>
        </div>

        {/* Variants Table */}
        <div className="card overflow-hidden">
          {isLoading ? (
            <div className="flex h-96 items-center justify-center">
              <div className="animate-pulse text-gray-400">Loading variants...</div>
            </div>
          ) : error ? (
            <div className="flex h-96 items-center justify-center text-red-500">
              Error loading variants
            </div>
          ) : data && data.variants.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Location</th>
                      <th>rsID</th>
                      <th>Gene</th>
                      <th>Change</th>
                      <th>Impact</th>
                      <th>Consequence</th>
                      <th>Genotype</th>
                      <th>ClinVar</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.variants.map((variant) => (
                      <VariantRow key={variant.id} variant={variant} />
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3">
                <div className="text-sm text-gray-600">
                  Showing {(page - 1) * pageSize + 1} to{' '}
                  {Math.min(page * pageSize, data.total)} of {data.total.toLocaleString()}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="rounded-lg border border-gray-200 p-2 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="px-3 text-sm">
                    Page {page} of {data.total_pages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                    disabled={page === data.total_pages}
                    className="rounded-lg border border-gray-200 p-2 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex h-96 flex-col items-center justify-center text-gray-400">
              <Filter className="h-12 w-12 mb-2" />
              <p>No variants found</p>
              <p className="text-sm">Try adjusting your filters or load a VCF file</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function VariantRow({ variant }: { variant: Variant }) {
  const clinvarClass = getClinVarClass(variant.clinvar?.clinical_significance);

  return (
    <tr className="hover:bg-gray-50">
      <td className="font-mono text-sm">
        {variant.chromosome}:{variant.position.toLocaleString()}
      </td>
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
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td>
        {variant.gene_symbol ? (
          <span className="font-medium">{variant.gene_symbol}</span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="font-mono text-sm">
        <span className="text-red-600">{variant.reference}</span>
        {' > '}
        <span className="text-green-600">{variant.alternate}</span>
        {variant.protein_change && (
          <div className="text-xs text-gray-500">{variant.protein_change}</div>
        )}
      </td>
      <td>
        {variant.impact ? (
          <span
            className={clsx(
              'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
              IMPACT_COLORS[variant.impact] ?? 'bg-gray-100 text-gray-600'
            )}
          >
            {variant.impact}
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="max-w-[200px] truncate text-sm text-gray-600">
        {variant.consequence?.replace(/_/g, ' ') ?? '-'}
      </td>
      <td className="font-mono text-sm">{variant.genotype ?? '-'}</td>
      <td>
        {variant.clinvar ? (
          <span
            className={clsx(
              'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
              clinvarClass
            )}
          >
            {formatClinVar(variant.clinvar.clinical_significance)}
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td>
        <div className="flex items-center gap-2">
          <Link
            to={`/analysis/${variant.id}`}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-primary-600"
            title="Analyze with AlphaGenome"
          >
            <Microscope className="h-4 w-4" />
          </Link>
          {variant.rsid && (
            <a
              href={`https://www.ncbi.nlm.nih.gov/clinvar/?term=${variant.rsid}`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-primary-600"
              title="View in ClinVar"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
      </td>
    </tr>
  );
}

function getClinVarClass(significance: string | null | undefined): string {
  if (!significance) return '';
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
    .join(' ')
    .substring(0, 20);
}
