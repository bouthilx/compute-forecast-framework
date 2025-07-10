# Paperoni vs Package Database Schema Comparison

**Date**: 2025-01-06
**Purpose**: Visual comparison of data models between Paperoni and Compute Forecast Package

## Paperoni Database Schema

```mermaid
erDiagram
    Paper {
        string id PK
        string title
        string abstract
        float[] quality
        datetime created
        datetime modified
        int citation_count
    }

    PaperAuthor {
        string id PK
        string paper_id FK
        string author_id FK
        int position
        float[] quality
    }

    Author {
        string id PK
        string name
        float[] quality
        datetime created
        datetime modified
    }

    AuthorName {
        string id PK
        string author_id FK
        string name
        float[] quality
    }

    Institution {
        string id PK
        string name
        string category
        float[] quality
    }

    Role {
        string id PK
        string author_id FK
        string institution_id FK
        datetime start_date
        datetime end_date
        float[] quality
    }

    Release {
        string id PK
        string paper_id FK
        string venue_id FK
        datetime date
        string date_precision
        float[] quality
    }

    Venue {
        string id PK
        string name
        string type
        string volume
        string publisher
        float[] quality
    }

    Link {
        string id PK
        string paper_id FK
        string url
        string type
        float[] quality
    }

    Topic {
        string id PK
        string paper_id FK
        string topic
        float[] quality
    }

    Flag {
        string id PK
        string paper_id FK
        string flag_type
        string comment
    }

    Researcher {
        string id PK
        string author_id FK
        string user
        string category
        datetime start_date
        datetime end_date
    }

    PaperMerge {
        string id PK
        string dest_id FK
        string src_id FK
        datetime created
    }

    AuthorMerge {
        string id PK
        string dest_id FK
        string src_id FK
        datetime created
    }

    ScraperData {
        string id PK
        string paper_id FK
        string scraper_id FK
        json data
        datetime created
    }

    ScraperID {
        string id PK
        string name
        string type
    }

    %% Relationships
    Paper ||--o{ PaperAuthor : has
    Paper ||--o{ Release : has
    Paper ||--o{ Link : has
    Paper ||--o{ Topic : has
    Paper ||--o{ Flag : has
    Paper ||--o{ ScraperData : tracked_by

    PaperAuthor }o--|| Author : references
    Author ||--o{ AuthorName : has_names
    Author ||--o{ Role : has_roles
    Author ||--o{ Researcher : tracked_as

    Role }o--|| Institution : at
    Release }o--|| Venue : published_in

    PaperMerge }o--|| Paper : merges_into
    PaperMerge }o--|| Paper : merged_from
    AuthorMerge }o--|| Author : merges_into
    AuthorMerge }o--|| Author : merged_from

    ScraperData }o--|| ScraperID : from_scraper
```

## Compute Forecast Package Schema

```mermaid
erDiagram
    Paper {
        string paper_id PK
        string title
        string abstract
        int year
        string venue
        int citations
        string doi
        string openalex_id
        string semantic_scholar_id
        string arxiv_id
        string collection_source
        datetime collection_timestamp
        string mila_affiliated
        string mila_domain
    }

    Author {
        string author_id PK
        string name
        string affiliation
    }

    PaperAuthor {
        string paper_id FK
        string author_id FK
        int position
    }

    CollectionResult {
        string id PK
        string source
        datetime collection_timestamp
        int success_count
        int failed_count
        json errors
    }

    CollectionQuery {
        string id PK
        string venue
        int year
        string institution
        string domain
        int min_citations
        int max_results
        json keywords
    }

    AnalysisResult {
        string id PK
        string paper_id FK
        string analysis_type
        json results
        datetime timestamp
    }

    ComputationalAnalysis {
        string paper_id FK
        bool uses_gpu
        float gpu_hours
        string gpu_types
        int parameters
        float training_time
        string frameworks
        string hardware_mentions
        float compute_score
        string extraction_method
    }

    AuthorshipAnalysis {
        string paper_id FK
        string primary_institution
        int author_count
        json affiliations
        float mila_affiliation_score
    }

    VenueAnalysis {
        string venue_name PK
        string venue_type
        float impact_score
        int total_papers
        float avg_citations
    }

    CitationStatistics {
        string paper_id FK
        int raw_citations
        float normalized_citations
        float impact_score
        string percentile_rank
    }

    QualityReport {
        string id PK
        string paper_id FK
        float metadata_completeness
        float extraction_confidence
        json validation_errors
        datetime created_at
    }

    ExtractionTemplate {
        string id PK
        string domain
        string pattern_type
        json patterns
        float confidence_threshold
    }

    SuppressionIndicator {
        string paper_id FK
        string indicator_type
        string evidence
        float confidence
    }

    %% Relationships
    Paper ||--o{ PaperAuthor : has
    Author ||--o{ PaperAuthor : writes
    Paper ||--o{ AnalysisResult : analyzed_by
    Paper ||--|| ComputationalAnalysis : has
    Paper ||--|| AuthorshipAnalysis : has
    Paper ||--|| CitationStatistics : has
    Paper ||--o{ QualityReport : validated_by
    Paper ||--o{ SuppressionIndicator : shows

    CollectionQuery ||--o{ CollectionResult : produces
    VenueAnalysis ||--o{ Paper : contains
    ExtractionTemplate ||--o{ ComputationalAnalysis : guides
```

## Key Schema Differences

### 1. **Model Complexity**
- **Paperoni**: 15+ interconnected tables with deep relationships
- **Package**: 12 tables with flatter structure focused on analysis

### 2. **Quality Tracking**
- **Paperoni**: Every entity has `quality` float array built-in
- **Package**: Separate `QualityReport` table for validation

### 3. **Author/Institution Handling**
- **Paperoni**: Complex graph (Author → Role → Institution)
- **Package**: Simple string affiliation on Author

### 4. **Venue Representation**
- **Paperoni**: Full `Venue` entity with type, volume, publisher
- **Package**: Simple string field on Paper

### 5. **Temporal Tracking**
- **Paperoni**: `created`/`modified` timestamps on all entities
- **Package**: Timestamps only where analytically relevant

### 6. **Identity Management**
- **Paperoni**: Single UUID system with merge tracking
- **Package**: Multiple external IDs (OpenAlex, S2, ArXiv)

### 7. **Data Source Tracking**
- **Paperoni**: `ScraperData` + `ScraperID` for full provenance
- **Package**: Simple `collection_source` string

### 8. **Analysis Integration**
- **Paperoni**: No analysis tables (separate system)
- **Package**: Built-in analysis tables (Computational, Authorship, etc.)

## Why Enhanced Models Bridge the Gap

The enhanced models (ScrapedPaper, ScrapedAuthor, VenueMetadata) act as an adapter layer:

```mermaid
graph LR
    A[Complex Paperoni Schema] --> B[Enhanced Models]
    B --> C[Simple Package Schema]
    B --> D[Preserved Metadata]

    style B fill:#f9f,stroke:#333,stroke-width:4px
```

They preserve the rich data from Paperoni's schema while providing clean conversion methods to fit the Package's analysis-focused structure.
