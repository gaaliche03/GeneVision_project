# Gene Prediction & Annotation Platform

## Overview
This project is a **bioinformatics web application** designed to automatically **predict and annotate genes** from unannotated genomic sequences.

With the rapid growth of genomic data, extracting meaningful biological insights has become a major challenge. This platform simplifies the process by integrating **data preprocessing, gene prediction, functional annotation, and 3D protein structure modeling** into a single, user-friendly interface.

<img width="998" height="176" alt="image" src="https://github.com/user-attachments/assets/d36405bd-d25d-4792-8ced-df5cccc25cab" />

---

## Key Features

### User Authentication
- Secure sign up / login system  
- User profile and history management  

### Sequence Input
- Upload or paste genomic sequences (FASTA format)  
- Automatic validation  

### Data Preprocessing
- FASTA parsing using Biopython  
- Sequence validation (alphabet check, invalid characters detection)  
- Filtering based on sequence length and GC content  
- DNA → RNA transcription  
- DNA → Protein translation  
- Data cleaning and formatting for downstream analysis  

### Gene Prediction
- Detection of coding regions from raw DNA sequences  
- Extraction of predicted genes and protein sequences  

### Functional Annotation
- Prediction of protein functions using Gene Ontology (GO)  
- Enrichment using biological databases  
- Simplified biological descriptions using LLM  

### Structural Annotation
- 3D protein structure prediction  
- Interactive visualization of molecular structures  

### Results Visualization
- Clear dashboards and summaries  
- Filtering and sorting of annotations  

### Report Generation
- Automatic PDF reports including all analysis results  

### History Tracking
- Save and revisit previous analyses  

---

## Tech Stack

### Backend & Processing
- Python  
- Biopython (SeqIO for preprocessing)  
- Pandas  

### Bioinformatics Tools
- **AUGUSTUS** → Gene prediction  
- **DeepGOPlus** → Functional annotation  
- **QuickGO API** → GO term enrichment  
- **ESM Atlas** → Protein structure prediction  

### AI Integration
- **LLM Gemini** → Simplification of biological descriptions  

### Frontend
- Streamlit  

### Database
- MongoDB  

---

## Workflow

1. Input genomic sequence (FASTA)  
2. Data preprocessing (validation, filtering, transformation)  
3. Gene prediction (AUGUSTUS)  
4. Protein extraction  
5. Functional annotation (DeepGOPlus + QuickGO)  
6. Description simplification (LLM)  
7. Structural prediction (ESM Atlas)  
8. Visualization & report generation  
