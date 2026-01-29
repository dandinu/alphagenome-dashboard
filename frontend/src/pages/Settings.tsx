import { useState } from 'react';
import { clsx } from 'clsx';
import {
  Settings as SettingsIcon,
  Key,
  Database,
  FolderOpen,
  CheckCircle,
  XCircle,
  RefreshCw,
  ExternalLink,
  Loader2,
  AlertCircle,
  Server,
} from 'lucide-react';
import Header from '../components/layout/Header';
import { useClinVarStatus, usePharmGKBStatus, useLoadedFiles } from '../hooks/useApi';
import { statusApi } from '../services/api';
import { useQuery } from '@tanstack/react-query';

export default function Settings() {
  const { data: apiStatus, isLoading: apiLoading, refetch: refetchApi } = useQuery({
    queryKey: ['api-status'],
    queryFn: statusApi.getStatus,
  });
  const { data: clinvarStatus, isLoading: clinvarLoading, refetch: refetchClinvar } = useClinVarStatus();
  const { data: pharmgkbStatus, isLoading: pharmgkbLoading, refetch: refetchPharmgkb } = usePharmGKBStatus();
  const { data: filesData, refetch: refetchFiles } = useLoadedFiles();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefreshAll = async () => {
    setIsRefreshing(true);
    await Promise.all([
      refetchApi(),
      refetchClinvar(),
      refetchPharmgkb(),
      refetchFiles(),
    ]);
    setIsRefreshing(false);
  };

  return (
    <div className="flex-1 overflow-auto">
      <Header
        title="Settings"
        subtitle="Configure your AlphaGenome dashboard"
      />

      <div className="p-6 max-w-4xl">
        {/* API Status */}
        <div className="card mb-6">
          <div className="card-header flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Server className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-medium text-gray-900">API Status</h3>
            </div>
            <button
              onClick={handleRefreshAll}
              disabled={isRefreshing}
              className="btn btn-secondary text-sm flex items-center gap-2"
            >
              <RefreshCw className={clsx('h-4 w-4', isRefreshing && 'animate-spin')} />
              Refresh
            </button>
          </div>
          <div className="card-body">
            {apiLoading ? (
              <div className="flex items-center gap-2 text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Checking API status...
              </div>
            ) : apiStatus ? (
              <div className="space-y-4">
                <StatusRow
                  label="Backend Status"
                  value={apiStatus.status}
                  status={apiStatus.status === 'healthy' ? 'success' : 'error'}
                />
                <StatusRow
                  label="AlphaGenome API"
                  value={apiStatus.alphagenome_configured ? 'Configured' : 'Not Configured'}
                  status={apiStatus.alphagenome_configured ? 'success' : 'warning'}
                />
                <StatusRow
                  label="VCF Data Directory"
                  value={apiStatus.vcf_data_dir}
                  status="info"
                  mono
                />
                <StatusRow
                  label="Annotations Directory"
                  value={apiStatus.annotations_dir}
                  status="info"
                  mono
                />
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-500">
                <XCircle className="h-4 w-4" />
                Unable to connect to backend
              </div>
            )}
          </div>
        </div>

        {/* AlphaGenome Configuration */}
        <div className="card mb-6">
          <div className="card-header">
            <div className="flex items-center gap-3">
              <Key className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-medium text-gray-900">
                AlphaGenome API Configuration
              </h3>
            </div>
          </div>
          <div className="card-body">
            <p className="text-sm text-gray-600 mb-4">
              The AlphaGenome API key is configured in the backend <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">.env</code> file.
              To update it, edit the following environment variables:
            </p>
            <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-100 overflow-x-auto">
              <div>ALPHAGENOME_API_KEY=your_api_key_here</div>
              <div>ALPHAGENOME_PROJECT_ID=your_project_id_here</div>
            </div>
            <div className="mt-4">
              <a
                href="https://deepmind.google.com/science/alphagenome/account/settings"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-primary-600 hover:underline"
              >
                Get your API key from AlphaGenome
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>

        {/* Annotation Databases */}
        <div className="card mb-6">
          <div className="card-header">
            <div className="flex items-center gap-3">
              <Database className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-medium text-gray-900">
                Annotation Databases
              </h3>
            </div>
          </div>
          <div className="card-body space-y-6">
            {/* ClinVar */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">ClinVar</h4>
                {clinvarLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                ) : clinvarStatus?.loaded ? (
                  <span className="inline-flex items-center gap-1 text-sm text-emerald-600">
                    <CheckCircle className="h-4 w-4" />
                    Loaded
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-sm text-amber-600">
                    <AlertCircle className="h-4 w-4" />
                    Not Loaded
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 mb-2">
                Database of clinically relevant genetic variants.
              </p>
              {clinvarStatus?.loaded ? (
                <div className="text-xs text-gray-500">
                  {clinvarStatus.variant_count?.toLocaleString()} variants loaded
                  {clinvarStatus.last_updated && (
                    <span className="ml-2">
                      | Updated: {new Date(clinvarStatus.last_updated).toLocaleDateString()}
                    </span>
                  )}
                </div>
              ) : (
                <div className="bg-amber-50 rounded-lg p-3 text-sm text-amber-800">
                  <p className="mb-2">
                    ClinVar data is not loaded. To download, run:
                  </p>
                  <code className="bg-amber-100 px-2 py-1 rounded text-xs block">
                    python scripts/download_clinvar.py
                  </code>
                </div>
              )}
            </div>

            <hr className="border-gray-200" />

            {/* PharmGKB */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">PharmGKB</h4>
                {pharmgkbLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                ) : pharmgkbStatus?.loaded ? (
                  <span className="inline-flex items-center gap-1 text-sm text-emerald-600">
                    <CheckCircle className="h-4 w-4" />
                    Loaded
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-sm text-amber-600">
                    <AlertCircle className="h-4 w-4" />
                    Not Loaded
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 mb-2">
                Pharmacogenomics knowledge for drug-gene interactions.
              </p>
              {pharmgkbStatus?.loaded ? (
                <div className="text-xs text-gray-500">
                  {pharmgkbStatus.annotation_count?.toLocaleString()} annotations loaded
                  {pharmgkbStatus.gene_count && (
                    <span className="ml-2">
                      | {pharmgkbStatus.gene_count} genes
                    </span>
                  )}
                </div>
              ) : (
                <div className="bg-amber-50 rounded-lg p-3 text-sm text-amber-800">
                  <p className="mb-2">
                    PharmGKB data is not loaded. To download, run:
                  </p>
                  <code className="bg-amber-100 px-2 py-1 rounded text-xs block">
                    python scripts/download_pharmgkb.py
                  </code>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Data Files */}
        <div className="card mb-6">
          <div className="card-header">
            <div className="flex items-center gap-3">
              <FolderOpen className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-medium text-gray-900">Loaded Data</h3>
            </div>
          </div>
          <div className="card-body">
            {filesData && filesData.files.length > 0 ? (
              <div className="space-y-3">
                {filesData.files.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
                  >
                    <div>
                      <p className="font-medium text-gray-900">{file.filename}</p>
                      <p className="text-xs text-gray-500">
                        {file.total_variants.toLocaleString()} variants |{' '}
                        {file.coding_variants.toLocaleString()} coding |
                        Loaded {new Date(file.loaded_at).toLocaleDateString()}
                      </p>
                    </div>
                    <CheckCircle className="h-5 w-5 text-emerald-500" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <FolderOpen className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                <p>No VCF files loaded</p>
                <p className="text-sm mt-1">
                  Place your VCF files in the <code className="bg-gray-100 px-1 rounded">data/vcf/</code> folder
                </p>
              </div>
            )}
          </div>
        </div>

        {/* About */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center gap-3">
              <SettingsIcon className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-medium text-gray-900">About</h3>
            </div>
          </div>
          <div className="card-body">
            <div className="space-y-3 text-sm text-gray-600">
              <p>
                <strong>AlphaGenome Dashboard</strong> is a personal genome analysis tool
                that integrates with Google DeepMind's AlphaGenome API.
              </p>
              <p>
                This dashboard helps you explore your whole genome sequencing data,
                identify clinically relevant variants, and understand potential drug
                interactions.
              </p>
              <div className="pt-3 flex flex-wrap gap-4">
                <a
                  href="https://deepmind.google.com/science/alphagenome"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary-600 hover:underline"
                >
                  AlphaGenome
                  <ExternalLink className="h-3 w-3" />
                </a>
                <a
                  href="https://www.ncbi.nlm.nih.gov/clinvar/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary-600 hover:underline"
                >
                  ClinVar
                  <ExternalLink className="h-3 w-3" />
                </a>
                <a
                  href="https://www.pharmgkb.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary-600 hover:underline"
                >
                  PharmGKB
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusRow({
  label,
  value,
  status,
  mono = false,
}: {
  label: string;
  value: string;
  status: 'success' | 'warning' | 'error' | 'info';
  mono?: boolean;
}) {
  const statusIcons = {
    success: <CheckCircle className="h-4 w-4 text-emerald-500" />,
    warning: <AlertCircle className="h-4 w-4 text-amber-500" />,
    error: <XCircle className="h-4 w-4 text-red-500" />,
    info: null,
  };

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-600">{label}</span>
      <div className="flex items-center gap-2">
        <span className={clsx('text-sm text-gray-900', mono && 'font-mono text-xs')}>
          {value}
        </span>
        {statusIcons[status]}
      </div>
    </div>
  );
}
