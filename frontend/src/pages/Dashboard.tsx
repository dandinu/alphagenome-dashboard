import { Link } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  FileSearch,
  Dna,
  AlertTriangle,
  Pill,
  TrendingUp,
  Database,
  ArrowRight,
} from 'lucide-react';
import Header from '../components/layout/Header';
import { useVariantStats, useLoadedFiles } from '../hooks/useApi';

const COLORS = ['#0ea5e9', '#f59e0b', '#10b981', '#6366f1', '#ec4899'];

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useVariantStats();
  const { data: filesData } = useLoadedFiles();

  const impactData = stats?.by_impact
    ? Object.entries(stats.by_impact).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  const chromosomeData = stats?.by_chromosome
    ? Object.entries(stats.by_chromosome)
        .sort((a, b) => {
          const aNum = parseInt(a[0].replace('chr', '')) || 99;
          const bNum = parseInt(b[0].replace('chr', '')) || 99;
          return aNum - bNum;
        })
        .slice(0, 12)
        .map(([name, value]) => ({
          name: name.replace('chr', ''),
          variants: value,
        }))
    : [];

  return (
    <div className="flex-1 overflow-auto">
      <Header
        title="Dashboard"
        subtitle="Overview of your genome analysis"
      />

      <div className="p-6">
        {/* Quick Stats */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            icon={Dna}
            label="Total Variants"
            value={stats?.total_variants?.toLocaleString() ?? '-'}
            subvalue={`${stats?.coding_variants?.toLocaleString() ?? '-'} coding`}
            color="bg-blue-500"
          />
          <StatCard
            icon={AlertTriangle}
            label="Pathogenic"
            value={stats?.clinvar_pathogenic?.toString() ?? '-'}
            subvalue="ClinVar flagged"
            color="bg-red-500"
          />
          <StatCard
            icon={Pill}
            label="Pharmacogenomic"
            value={stats?.pharmgkb_variants?.toString() ?? '-'}
            subvalue="Drug interactions"
            color="bg-purple-500"
          />
          <StatCard
            icon={Database}
            label="Files Loaded"
            value={filesData?.total?.toString() ?? '0'}
            subvalue="VCF files"
            color="bg-green-500"
          />
        </div>

        {/* Charts Row */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Variants by Chromosome */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">
                Variants by Chromosome
              </h3>
            </div>
            <div className="card-body">
              {statsLoading ? (
                <div className="flex h-64 items-center justify-center">
                  <div className="animate-pulse text-gray-400">Loading...</div>
                </div>
              ) : chromosomeData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={chromosomeData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="variants" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="No variant data available" />
              )}
            </div>
          </div>

          {/* Variants by Impact */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">
                Variants by Impact
              </h3>
            </div>
            <div className="card-body">
              {statsLoading ? (
                <div className="flex h-64 items-center justify-center">
                  <div className="animate-pulse text-gray-400">Loading...</div>
                </div>
              ) : impactData.length > 0 ? (
                <div className="flex items-center gap-8">
                  <ResponsiveContainer width="50%" height={280}>
                    <PieChart>
                      <Pie
                        data={impactData}
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, percent }) =>
                          `${name} (${(percent * 100).toFixed(0)}%)`
                        }
                        labelLine={false}
                      >
                        {impactData.map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={COLORS[index % COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 space-y-2">
                    {impactData.map((item, index) => (
                      <div key={item.name} className="flex items-center gap-2">
                        <div
                          className="h-3 w-3 rounded"
                          style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                        <span className="text-sm text-gray-600">{item.name}</span>
                        <span className="ml-auto font-medium">
                          {item.value.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState message="No impact data available" />
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-6">
          <h3 className="mb-4 text-lg font-medium text-gray-900">Quick Actions</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <QuickAction
              to="/files"
              icon={Database}
              title="Load VCF Data"
              description="Import your genome sequencing data"
            />
            <QuickAction
              to="/variants"
              icon={FileSearch}
              title="Explore Variants"
              description="Browse and filter your genetic variants"
            />
            <QuickAction
              to="/pharmacogenomics"
              icon={Pill}
              title="Drug Interactions"
              description="Check pharmacogenomic implications"
            />
          </div>
        </div>

        {/* ClinVar Summary */}
        {stats && (stats.clinvar_pathogenic > 0 || stats.clinvar_vus > 0) && (
          <div className="mt-6">
            <div className="card border-l-4 border-l-amber-500">
              <div className="card-body">
                <div className="flex items-start gap-4">
                  <AlertTriangle className="h-6 w-6 text-amber-500" />
                  <div>
                    <h3 className="font-medium text-gray-900">
                      ClinVar Annotations Found
                    </h3>
                    <p className="mt-1 text-sm text-gray-600">
                      Your genome contains{' '}
                      <span className="font-medium text-red-600">
                        {stats.clinvar_pathogenic} pathogenic
                      </span>{' '}
                      and{' '}
                      <span className="font-medium text-amber-600">
                        {stats.clinvar_vus} variants of uncertain significance
                      </span>
                      . Review these in the Disease Risk panel.
                    </p>
                    <Link
                      to="/disease-risk"
                      className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700"
                    >
                      View Disease Risk Panel
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  subvalue,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  subvalue: string;
  color: string;
}) {
  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center gap-4">
          <div className={`rounded-lg p-3 ${color}`}>
            <Icon className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="text-sm text-gray-500">{label}</p>
            <p className="text-2xl font-semibold text-gray-900">{value}</p>
            <p className="text-xs text-gray-400">{subvalue}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function QuickAction({
  to,
  icon: Icon,
  title,
  description,
}: {
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <Link
      to={to}
      className="card group transition-shadow hover:shadow-md"
    >
      <div className="card-body">
        <div className="flex items-center gap-4">
          <div className="rounded-lg bg-gray-100 p-3 transition-colors group-hover:bg-primary-100">
            <Icon className="h-6 w-6 text-gray-600 transition-colors group-hover:text-primary-600" />
          </div>
          <div>
            <h4 className="font-medium text-gray-900">{title}</h4>
            <p className="text-sm text-gray-500">{description}</p>
          </div>
          <ArrowRight className="ml-auto h-5 w-5 text-gray-400 transition-transform group-hover:translate-x-1" />
        </div>
      </div>
    </Link>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center text-gray-400">
      <TrendingUp className="h-12 w-12 mb-2" />
      <p>{message}</p>
      <Link
        to="/files"
        className="mt-2 text-sm text-primary-600 hover:underline"
      >
        Load VCF data to get started
      </Link>
    </div>
  );
}
