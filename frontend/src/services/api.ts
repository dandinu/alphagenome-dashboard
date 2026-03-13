import axios from 'axios';
import type {
  Variant,
  VariantListResponse,
  VariantStats,
  VCFFile,
  DiscoveredFile,
  VariantAnalysis,
  AnalysisResult,
  BatchJob,
  PharmacogenomicsPanel,
  DiseaseRiskPanel,
  ClinVarAnnotation,
  PharmGKBAnnotation,
  ApiStatus,
  VariantFilters,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============== Files API ==============

export const filesApi = {
  discover: async (): Promise<DiscoveredFile[]> => {
    const { data } = await api.get('/files');
    return data;
  },

  listLoaded: async (): Promise<{ files: VCFFile[]; total: number }> => {
    const { data } = await api.get('/files/loaded');
    return data;
  },

  parse: async (filename: string, codingOnly = true): Promise<VCFFile> => {
    const { data } = await api.post(`/files/${filename}/parse`, null, {
      params: { coding_only: codingOnly },
    });
    return data;
  },

  getStatus: async (fileId: number) => {
    const { data } = await api.get(`/files/${fileId}/status`);
    return data;
  },

  delete: async (fileId: number) => {
    const { data } = await api.delete(`/files/${fileId}`);
    return data;
  },
};

// ============== Variants API ==============

export const variantsApi = {
  list: async (
    page = 1,
    pageSize = 50,
    filters: VariantFilters = {}
  ): Promise<VariantListResponse> => {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('page_size', String(pageSize));

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value));
      }
    });

    const { data } = await api.get(`/variants?${params.toString()}`);
    return data;
  },

  get: async (variantId: number): Promise<Variant> => {
    const { data } = await api.get(`/variants/${variantId}`);
    return data;
  },

  getStats: async (vcfFileId?: number): Promise<VariantStats> => {
    const params = vcfFileId ? { vcf_file_id: vcfFileId } : {};
    const { data } = await api.get('/variants/stats', { params });
    return data;
  },

  getByGene: async (geneSymbol: string, page = 1, pageSize = 50) => {
    const { data } = await api.get(`/variants/by-gene/${geneSymbol}`, {
      params: { page, page_size: pageSize },
    });
    return data;
  },

  getByLocation: async (chromosome: string, start: number, end: number) => {
    const { data } = await api.get(
      `/variants/by-location/${chromosome}/${start}/${end}`
    );
    return data;
  },
};

// ============== Analysis API ==============

export const analysisApi = {
  getOutputTypes: async () => {
    const { data } = await api.get('/analysis/output-types');
    return data;
  },

  scoreVariant: async (
    variantId: number,
    analysisTypes: string[] = ['RNA_SEQ', 'SPLICE_SITES', 'ATAC']
  ): Promise<AnalysisResult[]> => {
    const { data } = await api.post('/analysis/score', {
      variant_id: variantId,
      analysis_types: analysisTypes,
    });
    return data;
  },

  batchScore: async (
    variantIds: number[],
    analysisTypes: string[] = ['RNA_SEQ', 'SPLICE_SITES']
  ): Promise<BatchJob> => {
    const { data } = await api.post('/analysis/batch', {
      variant_ids: variantIds,
      analysis_types: analysisTypes,
    });
    return data;
  },

  getJobStatus: async (jobId: string): Promise<BatchJob> => {
    const { data } = await api.get(`/analysis/job/${jobId}`);
    return data;
  },

  getVariantAnalysis: async (variantId: number): Promise<VariantAnalysis> => {
    const { data } = await api.get(`/analysis/${variantId}`);
    return data;
  },

  analyzeExpression: async (variantId: number, tissues?: string[]) => {
    const { data } = await api.post(`/analysis/expression/${variantId}`, {
      tissues,
    });
    return data;
  },

  analyzeSplicing: async (variantId: number) => {
    const { data } = await api.post(`/analysis/splicing/${variantId}`);
    return data;
  },

  analyzeHistone: async (variantId: number, tissues?: string[]) => {
    const { data } = await api.post(`/analysis/histone/${variantId}`, { tissues });
    return data;
  },

  analyzeTfBinding: async (variantId: number, tissues?: string[]) => {
    const { data } = await api.post(`/analysis/tf-binding/${variantId}`, { tissues });
    return data;
  },

  analyzeContacts: async (variantId: number, tissues?: string[]) => {
    const { data } = await api.post(`/analysis/contacts/${variantId}`, { tissues });
    return data;
  },

  analyzeIsm: async (variantId: number, windowSize = 50, outputTypes: string[] = ['RNA_SEQ']) => {
    const { data } = await api.post(`/analysis/ism/${variantId}`, {
      window_size: windowSize,
      output_types: outputTypes,
    });
    return data;
  },

  runFullAnalysis: async (variantId: number, tissues?: string[]) => {
    const { data } = await api.post(`/analysis/full/${variantId}`, null, {
      params: { tissues: tissues?.join(',') },
    });
    return data;
  },

  getPlotUrl: (variantId: number, analysisType: string) =>
    `/api/analysis/${variantId}/plot/${analysisType}`,
};

// ============== Annotations API ==============

export const annotationsApi = {
  clinvar: {
    getStatus: async () => {
      const { data } = await api.get('/annotations/clinvar/status');
      return data;
    },

    lookupByRsid: async (rsid: string): Promise<ClinVarAnnotation[]> => {
      const { data } = await api.get(`/annotations/clinvar/rsid/${rsid}`);
      return data;
    },

    lookupByGene: async (geneSymbol: string): Promise<ClinVarAnnotation[]> => {
      const { data } = await api.get(`/annotations/clinvar/gene/${geneSymbol}`);
      return data;
    },

    getPathogenic: async (geneSymbol?: string, limit = 100) => {
      const { data } = await api.get('/annotations/clinvar/pathogenic', {
        params: { gene_symbol: geneSymbol, limit },
      });
      return data;
    },
  },

  pharmgkb: {
    getStatus: async () => {
      const { data } = await api.get('/annotations/pharmgkb/status');
      return data;
    },

    lookupByRsid: async (rsid: string): Promise<PharmGKBAnnotation[]> => {
      const { data } = await api.get(`/annotations/pharmgkb/rsid/${rsid}`);
      return data;
    },

    lookupByGene: async (geneSymbol: string): Promise<PharmGKBAnnotation[]> => {
      const { data } = await api.get(`/annotations/pharmgkb/gene/${geneSymbol}`);
      return data;
    },

    lookupByDrug: async (drugName: string): Promise<PharmGKBAnnotation[]> => {
      const { data } = await api.get(`/annotations/pharmgkb/drug/${drugName}`);
      return data;
    },

    getPharmacogenes: async () => {
      const { data } = await api.get('/annotations/pharmgkb/genes');
      return data;
    },
  },

  panels: {
    getPharmacogenomics: async (
      vcfFileId?: number
    ): Promise<PharmacogenomicsPanel> => {
      const { data } = await api.get('/annotations/panels/pharmacogenomics', {
        params: { vcf_file_id: vcfFileId },
      });
      return data;
    },

    getDiseaseRisk: async (vcfFileId?: number): Promise<DiseaseRiskPanel> => {
      const { data } = await api.get('/annotations/panels/disease-risk', {
        params: { vcf_file_id: vcfFileId },
      });
      return data;
    },
  },
};

// ============== Status API ==============

export const statusApi = {
  getHealth: async () => {
    const { data } = await api.get('/health');
    return data;
  },

  getStatus: async (): Promise<ApiStatus> => {
    const { data } = await api.get('/status');
    return data;
  },
};

export default api;
