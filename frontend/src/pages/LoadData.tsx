import { useState } from 'react';
import { Upload, File, Check, Loader2, Trash2 } from 'lucide-react';
import Header from '../components/layout/Header';
import { useDiscoveredFiles, useLoadedFiles, useParseFile, useFileStatus } from '../hooks/useApi';
import type { DiscoveredFile, VCFFile } from '../types';

export default function LoadData() {
  const [loadingFile, setLoadingFile] = useState<string | null>(null);
  const [loadedFileId, setLoadedFileId] = useState<number | null>(null);

  const { data: discoveredFiles, isLoading: discovering } = useDiscoveredFiles();
  const { data: loadedFilesData, refetch: refetchLoaded } = useLoadedFiles();
  const parseFile = useParseFile();
  const { data: fileStatus } = useFileStatus(loadedFileId);

  const loadedFiles = loadedFilesData?.files ?? [];
  const loadedFilenames = new Set(loadedFiles.map((f) => f.filename));

  const handleLoadFile = async (filename: string) => {
    setLoadingFile(filename);
    try {
      const result = await parseFile.mutateAsync({ filename, codingOnly: true });
      setLoadedFileId(result.id);
    } catch (error) {
      console.error('Error loading file:', error);
    } finally {
      setLoadingFile(null);
    }
  };

  return (
    <div className="flex-1 overflow-auto">
      <Header
        title="Load Data"
        subtitle="Import your VCF files for analysis"
      />

      <div className="p-6">
        {/* Instructions */}
        <div className="card mb-6 border-l-4 border-l-primary-500">
          <div className="card-body">
            <h3 className="font-medium text-gray-900">Getting Started</h3>
            <p className="mt-1 text-sm text-gray-600">
              Place your VCF files in the <code className="rounded bg-gray-100 px-1 py-0.5">data/vcf/</code> folder.
              Supported formats: <code>.vcf</code> and <code>.vcf.gz</code>
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Available Files */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">Available Files</h3>
              <p className="text-sm text-gray-500">Files found in data/vcf/</p>
            </div>
            <div className="card-body">
              {discovering ? (
                <div className="flex items-center justify-center py-8 text-gray-400">
                  <Loader2 className="h-6 w-6 animate-spin mr-2" />
                  Scanning for files...
                </div>
              ) : discoveredFiles && discoveredFiles.length > 0 ? (
                <div className="space-y-3">
                  {discoveredFiles.map((file) => (
                    <FileCard
                      key={file.filename}
                      file={file}
                      isLoaded={loadedFilenames.has(file.filename)}
                      isLoading={loadingFile === file.filename}
                      onLoad={() => handleLoadFile(file.filename)}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-gray-400">
                  <Upload className="h-12 w-12 mb-2" />
                  <p>No VCF files found</p>
                  <p className="text-sm">
                    Place files in <code>data/vcf/</code>
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Loaded Files */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">Loaded Files</h3>
              <p className="text-sm text-gray-500">Files ready for analysis</p>
            </div>
            <div className="card-body">
              {loadedFiles.length > 0 ? (
                <div className="space-y-3">
                  {loadedFiles.map((file) => (
                    <LoadedFileCard key={file.id} file={file} />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-gray-400">
                  <File className="h-12 w-12 mb-2" />
                  <p>No files loaded yet</p>
                  <p className="text-sm">Select a file to load</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Loading Progress */}
        {fileStatus && fileStatus.status === 'loading' && (
          <div className="mt-6 card">
            <div className="card-body">
              <div className="flex items-center gap-4">
                <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
                <div className="flex-1">
                  <p className="font-medium text-gray-900">Loading variants...</p>
                  <p className="text-sm text-gray-500">
                    {fileStatus.loaded_variants.toLocaleString()} of{' '}
                    {fileStatus.coding_variants.toLocaleString()} coding variants
                  </p>
                  <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
                    <div
                      className="h-2 rounded-full bg-primary-500 transition-all"
                      style={{
                        width: `${
                          (fileStatus.loaded_variants / fileStatus.coding_variants) * 100
                        }%`,
                      }}
                    />
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

function FileCard({
  file,
  isLoaded,
  isLoading,
  onLoad,
}: {
  file: DiscoveredFile;
  isLoaded: boolean;
  isLoading: boolean;
  onLoad: () => void;
}) {
  const sizeFormatted = formatBytes(file.size_bytes);

  return (
    <div className="flex items-center gap-4 rounded-lg border border-gray-200 p-4">
      <File className="h-8 w-8 text-gray-400" />
      <div className="flex-1">
        <p className="font-medium text-gray-900">{file.filename}</p>
        <p className="text-sm text-gray-500">{sizeFormatted}</p>
      </div>
      {isLoaded ? (
        <div className="flex items-center gap-2 text-green-600">
          <Check className="h-5 w-5" />
          <span className="text-sm font-medium">Loaded</span>
        </div>
      ) : (
        <button
          onClick={onLoad}
          disabled={isLoading}
          className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              Load
            </>
          )}
        </button>
      )}
    </div>
  );
}

function LoadedFileCard({ file }: { file: VCFFile }) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-green-200 bg-green-50 p-4">
      <div className="rounded-full bg-green-100 p-2">
        <Check className="h-5 w-5 text-green-600" />
      </div>
      <div className="flex-1">
        <p className="font-medium text-gray-900">{file.filename}</p>
        <p className="text-sm text-gray-600">
          {file.coding_variants.toLocaleString()} coding variants
          {file.sample_name && ` • ${file.sample_name}`}
        </p>
      </div>
      <div className="text-right">
        <p className="text-sm text-gray-500">
          Loaded {new Date(file.loaded_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
