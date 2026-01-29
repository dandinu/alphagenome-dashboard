// Variant types
export interface Variant {
  id: number;
  vcf_file_id: number;
  chromosome: string;
  position: number;
  rsid: string | null;
  reference: string;
  alternate: string;
  quality: number | null;
  filter_status: string | null;
  genotype: string | null;
  zygosity: string | null;
  variant_type: string | null;
  is_coding: boolean;
  gene_symbol: string | null;
  gene_id: string | null;
  transcript_id: string | null;
  consequence: string | null;
  impact: string | null;
  protein_change: string | null;
  codon_change: string | null;
  af_gnomad: number | null;
  af_1000g: number | null;
  created_at: string;
  clinvar?: ClinVarAnnotation;
  pharmgkb?: PharmGKBAnnotation[];
  has_analysis: boolean;
}

export interface VariantListResponse {
  variants: Variant[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface VariantStats {
  total_variants: number;
  coding_variants: number;
  snps: number;
  indels: number;
  by_chromosome: Record<string, number>;
  by_impact: Record<string, number>;
  by_consequence: Record<string, number>;
  clinvar_pathogenic: number;
  clinvar_benign: number;
  clinvar_vus: number;
  pharmgkb_variants: number;
}

// VCF File types
export interface VCFFile {
  id: number;
  filename: string;
  filepath: string;
  sample_name: string | null;
  total_variants: number;
  coding_variants: number;
  loaded_at: string;
}

export interface DiscoveredFile {
  filename: string;
  filepath: string;
  size_bytes: number;
  modified: number;
}

// Annotation types
export interface ClinVarAnnotation {
  id: number;
  clinvar_id: string | null;
  rsid: string | null;
  clinical_significance: string | null;
  review_status: string | null;
  disease_names: string | null;
  disease_ids: string | null;
  gene_symbol: string | null;
  last_updated: string | null;
}

export interface PharmGKBAnnotation {
  id: number;
  rsid: string | null;
  gene_symbol: string | null;
  drug_name: string | null;
  drug_id: string | null;
  phenotype_category: string | null;
  significance: string | null;
  guideline_name: string | null;
  allele: string | null;
  annotation_text: string | null;
  level_of_evidence: string | null;
}

// Analysis types
export interface AnalysisResult {
  id: number;
  variant_id: number;
  analysis_type: string;
  score: number | null;
  score_details: Record<string, unknown> | null;
  plot_data: Record<string, unknown> | null;
  model_version: string | null;
  analyzed_at: string;
}

export interface VariantAnalysis {
  variant: Variant;
  analyses: AnalysisResult[];
  expression_impact: Record<string, unknown> | null;
  splicing_impact: Record<string, unknown> | null;
  chromatin_impact: Record<string, unknown> | null;
}

export interface BatchJob {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  total_variants: number;
  completed: number;
  failed: number;
  created_at: string;
}

// Panel types
export interface PharmaGeneReport {
  gene_symbol: string;
  gene_name: string;
  variants: Variant[];
  drugs: DrugAssociation[];
  diplotype: string | null;
  phenotype: string | null;
  recommendations: string[];
}

export interface DrugAssociation {
  drug_name: string;
  drug_id: string;
  annotations: unknown[];
  highest_evidence: string | null;
}

export interface PharmacogenomicsPanel {
  genes: PharmaGeneReport[];
  total_actionable_variants: number;
  summary: string;
}

export interface DiseaseRiskVariant {
  variant: Variant;
  disease_name: string;
  disease_id: string | null;
  clinical_significance: string;
  inheritance: string | null;
  risk_category: 'high' | 'moderate' | 'low' | 'unknown';
}

export interface DiseaseRiskPanel {
  pathogenic_variants: DiseaseRiskVariant[];
  likely_pathogenic_variants: DiseaseRiskVariant[];
  risk_factors: DiseaseRiskVariant[];
  total_high_risk: number;
  total_moderate_risk: number;
  summary: string;
}

// API status
export interface ApiStatus {
  status: string;
  vcf_data_dir: string;
  annotations_dir: string;
  alphagenome_configured: boolean;
  endpoints: Record<string, string>;
}

// Filter types
export interface VariantFilters {
  chromosome?: string;
  gene_symbol?: string;
  rsid?: string;
  is_coding?: boolean;
  impact?: string;
  consequence?: string;
  zygosity?: string;
  min_quality?: number;
  search?: string;
  vcf_file_id?: number;
}
