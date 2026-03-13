import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { variantsApi, filesApi, analysisApi, annotationsApi } from '../services/api';
import type { VariantFilters } from '../types';

// ============== Variants Hooks ==============

export function useVariants(page = 1, pageSize = 50, filters: VariantFilters = {}) {
  return useQuery({
    queryKey: ['variants', page, pageSize, filters],
    queryFn: () => variantsApi.list(page, pageSize, filters),
    placeholderData: (previousData) => previousData,
  });
}

export function useVariant(variantId: number | null) {
  return useQuery({
    queryKey: ['variant', variantId],
    queryFn: () => variantsApi.get(variantId!),
    enabled: variantId !== null,
  });
}

export function useVariantStats(vcfFileId?: number) {
  return useQuery({
    queryKey: ['variant-stats', vcfFileId],
    queryFn: () => variantsApi.getStats(vcfFileId),
  });
}

// ============== Files Hooks ==============

export function useDiscoveredFiles() {
  return useQuery({
    queryKey: ['discovered-files'],
    queryFn: filesApi.discover,
  });
}

export function useLoadedFiles() {
  return useQuery({
    queryKey: ['loaded-files'],
    queryFn: filesApi.listLoaded,
  });
}

export function useParseFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ filename, codingOnly }: { filename: string; codingOnly?: boolean }) =>
      filesApi.parse(filename, codingOnly),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['loaded-files'] });
      queryClient.invalidateQueries({ queryKey: ['variants'] });
      queryClient.invalidateQueries({ queryKey: ['variant-stats'] });
    },
  });
}

export function useFileStatus(fileId: number | null) {
  return useQuery({
    queryKey: ['file-status', fileId],
    queryFn: () => filesApi.getStatus(fileId!),
    enabled: fileId !== null,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === 'loading' ? 2000 : false;
    },
  });
}

// ============== Analysis Hooks ==============

export function useVariantAnalysis(variantId: number | null) {
  return useQuery({
    queryKey: ['variant-analysis', variantId],
    queryFn: () => analysisApi.getVariantAnalysis(variantId!),
    enabled: variantId !== null,
  });
}

export function useScoreVariant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ variantId, analysisTypes }: { variantId: number; analysisTypes?: string[] }) =>
      analysisApi.scoreVariant(variantId, analysisTypes),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['variant-analysis', variables.variantId] });
      queryClient.invalidateQueries({ queryKey: ['variant', variables.variantId] });
    },
  });
}

export function useBatchScore() {
  return useMutation({
    mutationFn: ({ variantIds, analysisTypes }: { variantIds: number[]; analysisTypes?: string[] }) =>
      analysisApi.batchScore(variantIds, analysisTypes),
  });
}

export function useHistoneAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ variantId, tissues }: { variantId: number; tissues?: string[] }) =>
      analysisApi.analyzeHistone(variantId, tissues),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['variant-analysis', variables.variantId] });
    },
  });
}

export function useTfBindingAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ variantId, tissues }: { variantId: number; tissues?: string[] }) =>
      analysisApi.analyzeTfBinding(variantId, tissues),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['variant-analysis', variables.variantId] });
    },
  });
}

export function useContactsAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ variantId, tissues }: { variantId: number; tissues?: string[] }) =>
      analysisApi.analyzeContacts(variantId, tissues),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['variant-analysis', variables.variantId] });
    },
  });
}

export function useIsmAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ variantId, windowSize, outputTypes }: { variantId: number; windowSize?: number; outputTypes?: string[] }) =>
      analysisApi.analyzeIsm(variantId, windowSize, outputTypes),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['variant-analysis', variables.variantId] });
    },
  });
}

export function useFullAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ variantId, tissues }: { variantId: number; tissues?: string[] }) =>
      analysisApi.runFullAnalysis(variantId, tissues),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['variant-analysis', variables.variantId] });
    },
  });
}

export function useBatchJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['batch-job', jobId],
    queryFn: () => analysisApi.getJobStatus(jobId!),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === 'running' || data?.status === 'queued' ? 3000 : false;
    },
  });
}

export function useOutputTypes() {
  return useQuery({
    queryKey: ['output-types'],
    queryFn: analysisApi.getOutputTypes,
    staleTime: Infinity,
  });
}

// ============== Annotation Hooks ==============

export function usePharmacogenomicsPanel(vcfFileId?: number) {
  return useQuery({
    queryKey: ['pharmacogenomics-panel', vcfFileId],
    queryFn: () => annotationsApi.panels.getPharmacogenomics(vcfFileId),
  });
}

export function useDiseaseRiskPanel(vcfFileId?: number) {
  return useQuery({
    queryKey: ['disease-risk-panel', vcfFileId],
    queryFn: () => annotationsApi.panels.getDiseaseRisk(vcfFileId),
  });
}

export function useClinVarStatus() {
  return useQuery({
    queryKey: ['clinvar-status'],
    queryFn: annotationsApi.clinvar.getStatus,
  });
}

export function usePharmGKBStatus() {
  return useQuery({
    queryKey: ['pharmgkb-status'],
    queryFn: annotationsApi.pharmgkb.getStatus,
  });
}

export function usePharmacogenes() {
  return useQuery({
    queryKey: ['pharmacogenes'],
    queryFn: annotationsApi.pharmgkb.getPharmacogenes,
    staleTime: Infinity,
  });
}
