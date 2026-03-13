# AlphaGenome Dashboard - User Guide

A practical guide to using each section of the dashboard and interpreting the results.

---

## Table of Contents

1. [Dashboard](#dashboard)
2. [Load Data](#load-data)
3. [Variant Explorer](#variant-explorer)
4. [Variant Analysis (AlphaGenome)](#variant-analysis)
   - [Score Details](#score-details)
   - [Prediction Track](#prediction-track)
   - [Analysis Types](#analysis-types)
   - [Epigenomic Summary Cards](#epigenomic-summary-cards)
   - [Composite Splicing Score](#composite-splicing-score)
5. [Pharmacogenomics](#pharmacogenomics)
6. [Disease Risk](#disease-risk)

---

## Dashboard

The landing page shows a summary of your loaded genome data.

| Field | What It Means |
|---|---|
| **Total Variants** | Number of variants loaded from your VCF files |
| **Coding Variants** | Variants that fall within protein-coding regions |
| **SNPs / Indels** | Single nucleotide changes vs. insertions/deletions |
| **Variants by Chromosome** | Distribution chart showing variant count per chromosome. Larger chromosomes naturally have more variants. |
| **Variants by Impact** | Breakdown by predicted functional impact (HIGH, MODERATE, LOW, MODIFIER) |
| **ClinVar Pathogenic** | How many of your variants are classified as disease-causing in ClinVar |
| **PharmGKB Variants** | How many of your variants have known drug-gene interactions |

**Example**: If you see "ClinVar Pathogenic: 3", that means 3 of your variants have been independently classified as disease-causing. Navigate to Disease Risk for details.

---

## Load Data

This is where you import your VCF (Variant Call Format) files.

### How to use

1. Place your `.vcf` or `.vcf.gz` files in the `data/vcf/` directory
2. Open the Load Data page - your files appear under "Discovered Files"
3. Click **Parse** to load a file into the database
4. Optionally check "Coding only" to skip non-coding variants (faster loading, smaller dataset)

### What to know

- **Supported formats**: `.vcf`, `.vcf.gz` (gzipped recommended for whole-genome files)
- **Variant types**: SNPs, indels, CNVs, and structural variants are all loaded
- **No annotations required**: Your VCF does not need rsIDs, VEP, or SnpEff annotations. The dashboard matches variants by position.
- **Assembly**: Your VCF should be aligned to GRCh37 (hg19) or GRCh38 (hg38). Set `GENOME_ASSEMBLY` in `.env` to match. The dashboard automatically lifts over coordinates to GRCh38 for AlphaGenome analysis.

---

## Variant Explorer

A searchable, filterable table of all your loaded variants.

### Columns

| Column | Meaning |
|---|---|
| **Gene** | The gene this variant falls in (if coding) |
| **rsID** | The dbSNP reference ID (e.g., rs1234567), if available |
| **Location** | Chromosome and position (e.g., 1:10,146) |
| **Change** | Reference allele > Alternate allele (e.g., `A > G`) |
| **Type** | SNP, DEL, INS, or other variant type |
| **Zygosity** | Heterozygous (one copy) or Homozygous (both copies) |
| **Impact** | Predicted functional impact from variant annotation |

### Impact levels

- **HIGH**: Likely disrupts protein function (stop gained, frameshift, splice donor/acceptor)
- **MODERATE**: Might change protein function (missense, in-frame indel)
- **LOW**: Unlikely to change protein behaviour (synonymous, splice region)
- **MODIFIER**: Non-coding or intergenic, effect unclear

### Filters

Use the filter bar to narrow down by chromosome, gene, impact level, zygosity, coding status, or free-text search.

**Example**: Filter by Impact = HIGH and Gene = BRCA1 to find high-impact variants in the BRCA1 gene.

---

## Variant Analysis

This is the core of the dashboard. Select a variant and run AlphaGenome's deep learning model to predict its functional effects.

### How to use

1. Navigate to **Analysis** in the sidebar
2. Search for a variant by gene name, rsID, or position
3. Click a variant to open its analysis page
4. Click **Full Analysis** (runs all analysis types) or select specific types and click **Run Selected**
5. Expand each result card to see score details and prediction tracks

### Score Details

When you expand a result card (e.g., RNA SEQ), you see per-scorer breakdowns:

| Scorer | What It Measures |
|---|---|
| **Center Mask** | General effect of the variant on any output type. Masks the variant position and measures how much the prediction changes. |
| **Gene Mask LFC** | Log fold-change in gene expression. Positive = increased expression, negative = decreased. |
| **Gene Mask Active** | Whether the variant changes the active/inactive state of a gene. Higher values = larger state change. |
| **Gene Mask Splicing** | Effect on splice site recognition. High values suggest the variant disrupts normal splicing. |
| **Splice Junction** | Changes at specific splice junctions. Non-zero values mean a junction is created or destroyed. |
| **Polyadenylation** | Effect on mRNA 3' end processing. Changes here can affect mRNA stability. |
| **Contact Map** | Changes to 3D chromatin folding. Can indicate disruption of gene regulation at a distance. |

#### Per-scorer statistics

Each scorer shows:

- **Mean**: Average effect across all tracks (tissues/cell types). A mean near 0 means most tissues are unaffected.
- **Max**: Largest effect in any single track. This is the most important number - it shows the worst-case tissue.
- **Min**: Largest negative effect.
- **Std**: How much the effect varies across tissues. High std = tissue-specific effect.
- **N Tracks**: Number of tissue/cell-type tracks scored.

**Example interpretation**: An RNA SEQ result with Gene Mask LFC `max = 0.388` means the variant causes up to a 0.388 log-fold-change in gene expression in at least one tissue. This is a moderate effect. Values above 1.0 are large effects; values below 0.05 are negligible.

### Prediction Track

The chart below the score details shows a simulated REF vs ALT comparison:

- **Green line (Reference)**: Model prediction for the reference allele
- **Red line (Alternate)**: Model prediction for the alternate allele
- **X-axis**: Genomic position relative to the variant (0 = variant site)
- **Y-axis**: Predicted signal intensity

Where the two lines diverge, the variant is changing the predicted signal. Larger divergence = stronger effect.

### Analysis Types

| Type | What It Predicts | When It Matters |
|---|---|---|
| **RNA-seq** | Gene expression levels across 667 tissues | Always relevant. Shows if a variant changes how much a gene is expressed. |
| **CAGE** | Transcription start site activity (546 tracks) | Important for promoter variants. |
| **PRO-CAP** | TSS activity (12 tracks) | Similar to CAGE, fewer tracks. |
| **ATAC-seq** | Open chromatin / accessibility (167 tracks) | Relevant for regulatory variants. Open chromatin = gene can be turned on. |
| **DNase-seq** | Chromatin accessibility (305 tracks) | Similar to ATAC, different assay. |
| **Histone Marks** | Histone modifications (1,116 tracks) | Shows epigenomic state changes - see [Epigenomic Summary](#epigenomic-summary-cards). |
| **TF Binding** | Transcription factor binding (1,617 tracks) | Shows if a variant creates or destroys a TF binding site. |
| **3D Contacts** | Chromatin 3D structure (28 tracks) | Shows if a variant disrupts long-range gene regulation. |
| **Splice Sites** | Splice site strength (4 tracks) | Critical for variants near exon-intron boundaries. |
| **Splice Junctions** | Junction usage (734 tracks) | Shows exon skipping or novel junction creation. |
| **Splice Usage** | Splice site usage fraction (734 tracks) | Proportion of transcripts using each splice site. |

**Example**: A variant at a splice donor site (GT dinucleotide) would show a high Splice Sites score. If the Splice Junctions score also changes, it means the variant causes exon skipping or intron retention.

### Epigenomic Summary Cards

When you run a Full Analysis, three summary cards appear at the bottom:

#### Histone Marks
Shows how the variant changes histone modifications. Key marks:

| Mark | Meaning |
|---|---|
| **H3K27ac** | Active enhancers and promoters. Loss = gene may be silenced. |
| **H3K4me3** | Active promoters. Loss = transcription may decrease. |
| **H3K36me3** | Actively transcribed gene bodies. |
| **H3K27me3** | Repressed/silenced regions. Gain = gene may be turned off. |
| **H3K9ac** | Active regulatory regions. |

**Example**: If H3K27ac shows `change: -0.3, direction: decreased`, the variant is reducing enhancer activity, which could lower expression of nearby genes.

#### TF Binding
Shows which transcription factors gain or lose binding at the variant site.

- **Disrupted TFs**: TFs that lose binding (variant destroys the binding motif)
- **Created TFs**: TFs that gain binding (variant creates a new motif)
- **Peak change**: Magnitude of the binding change

**Example**: "CTCF: peak_change = -0.45, direction = lost" means the variant disrupts a CTCF insulator binding site. CTCF organizes 3D chromatin structure, so this could affect regulation of genes in the surrounding region.

#### 3D Contacts
Shows changes to chromatin looping and TAD (Topologically Associating Domain) boundaries.

- **Max change**: Largest contact frequency change
- **Contact score change**: Sum of all changes

**Example**: A high contact score change near a TAD boundary could mean the variant disrupts the boundary, allowing genes in one domain to be regulated by enhancers in an adjacent domain.

### Composite Splicing Score

Displayed prominently on the variant info card when available. This combines multiple splicing metrics into one number:

```
composite_splicing = max(splice_sites) + max(splice_site_usage) + max(splice_junctions) / 5.0
```

| Score Range | Interpretation |
|---|---|
| 0 - 0.1 | No splicing impact |
| 0.1 - 0.5 | Mild splicing effect |
| 0.5 - 2.0 | Moderate splicing disruption |
| > 2.0 | Strong splicing disruption - likely pathogenic if in a disease gene |

---

## Pharmacogenomics

Shows how your genetic variants affect drug response, using data from PharmGKB.

### What you see

Each gene card shows:

- **Gene name**: The pharmacogene (e.g., CYP2D6, CYP2C19, DPYD)
- **Variants found**: Your variants in this gene
- **Associated drugs**: Medications affected by this gene
- **Evidence level**: Strength of the drug-gene association

### Evidence levels

| Level | Meaning |
|---|---|
| **1A** | Guideline-level evidence (CPIC/DPWG). Action is recommended. |
| **1B** | Strong evidence of association. Likely clinically actionable. |
| **2A** | Moderate evidence. Consider for clinical decisions. |
| **2B** | Limited evidence. Emerging association. |
| **3** | Single study. Needs confirmation. |
| **4** | Case reports only. Preliminary. |

**Example**: If you have a CYP2D6 variant with evidence level 1A for codeine, it means clinical guidelines recommend adjusting your codeine dose based on your genotype. CYP2D6 poor metabolizers cannot convert codeine to morphine, making the drug ineffective.

### Common pharmacogenes

| Gene | Affects |
|---|---|
| **CYP2D6** | Codeine, tramadol, tamoxifen, many antidepressants |
| **CYP2C19** | Clopidogrel (Plavix), proton pump inhibitors, some antidepressants |
| **CYP2C9** | Warfarin, NSAIDs |
| **DPYD** | Fluoropyrimidines (5-FU, capecitabine) - cancer chemotherapy |
| **TPMT** | Azathioprine, mercaptopurine - immunosuppressants |
| **SLCO1B1** | Statins (simvastatin) - cholesterol medication |
| **HLA-B** | Carbamazepine, abacavir - hypersensitivity reactions |

---

## Disease Risk

Shows variants in your genome that are classified as disease-causing or disease-associated in ClinVar.

### Categories

| Category | What It Means |
|---|---|
| **Pathogenic** | Strong evidence this variant causes disease. Most clinically significant. |
| **Likely Pathogenic** | Probable disease-causing variant. High confidence but less evidence than Pathogenic. |
| **Risk Factor** | Associated with increased disease risk but not directly causative. |

### What each variant shows

- **Gene**: The affected gene
- **Disease**: The associated condition(s)
- **Clinical Significance**: ClinVar classification
- **Risk Category**: HIGH (pathogenic), MODERATE (likely pathogenic), LOW (risk factor)

### How to interpret

- **Heterozygous pathogenic variant in a recessive gene**: You are a carrier but likely unaffected. Your children could be affected if the other parent also carries a variant in the same gene.
- **Heterozygous pathogenic variant in a dominant gene**: You may be affected or at risk. Penetrance varies by gene.
- **Homozygous pathogenic variant**: Both copies are affected. For recessive conditions, this typically means you are affected.

**Example**: A heterozygous pathogenic variant in CFTR (cystic fibrosis gene) means you are a carrier. CF is recessive, so you need two copies to have the disease. However, a heterozygous pathogenic variant in BRCA1 significantly increases breast and ovarian cancer risk because BRCA1 follows a dominant inheritance pattern for cancer predisposition.

### Important notes

- This is not a clinical diagnosis. Always consult a genetic counselor or physician.
- ClinVar classifications are based on published evidence and can change over time.
- Many variants are classified as "Uncertain Significance" (VUS) - these are excluded from the Disease Risk panel but visible in the Variant Explorer.
- Population frequency matters: a "pathogenic" variant that is common (>1% frequency) in your ancestry group may actually be benign. Check the gnomAD frequency in the Variant Explorer.
