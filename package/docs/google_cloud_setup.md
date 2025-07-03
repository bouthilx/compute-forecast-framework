# Google Cloud Vision Setup Guide

This guide explains how to set up Google Cloud Vision for PDF OCR processing in the compute forecast analysis package.

## Prerequisites

- Google Cloud Platform account
- Project with billing enabled
- PDF processing needs for difficult scanned documents

## Setup Steps

### 1. Enable Google Cloud Vision API

```bash
# Using gcloud CLI
gcloud services enable vision.googleapis.com

# Or enable via Console:
# https://console.cloud.google.com/apis/library/vision.googleapis.com
```

### 2. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create pdf-vision-processor \
    --description="Service account for PDF Vision processing" \
    --display-name="PDF Vision Processor"

# Get your project ID
PROJECT_ID=$(gcloud config get-value project)

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:pdf-vision-processor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudvision.admin"
```

### 3. Download Credentials

```bash
# Create and download credentials
gcloud iam service-accounts keys create ~/google-cloud-credentials.json \
    --iam-account=pdf-vision-processor@$PROJECT_ID.iam.gserviceaccount.com
```

### 4. Configure Environment

```bash
# Set environment variable (add to your ~/.bashrc or ~/.zshrc)
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/google-cloud-credentials.json"

# Or set in your application configuration
```

## Usage

### Basic Integration

```python
from pathlib import Path
from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.extractors.google_vision_extractor import GoogleCloudVisionExtractor

# Initialize processor
config = {
    'extraction': {
        'max_pages': 2,
        'min_confidence': 0.5
    }
}
processor = OptimizedPDFProcessor(config)

# Initialize Google Vision extractor
credentials_path = "/path/to/google-cloud-credentials.json"
google_extractor = GoogleCloudVisionExtractor(credentials_path)

# Register as fallback extractor (level 3 = low priority, cost-controlled)
processor.register_extractor('google_vision', google_extractor, level=3)

# Process PDF - Google Vision will only be used if other methods fail
paper_metadata = {
    'title': 'Research Paper Title',
    'authors': ['Author Name']
}

result = processor.process_pdf(
    Path("/path/to/scanned_paper.pdf"),
    paper_metadata
)

# Check if Google Vision was used and review costs
if result.get('method') == 'google_cloud_vision':
    print(f"Used Google Cloud Vision - Cost: ${result.get('cost', 0):.4f}")
    
cost_summary = processor.get_cost_summary()
print(f"Total costs: ${cost_summary['total_cost']:.4f}")
```

### Standalone Usage

```python
from src.pdf_parser.extractors.google_vision_extractor import GoogleCloudVisionExtractor

# Initialize extractor
extractor = GoogleCloudVisionExtractor("/path/to/credentials.json")

# Extract from first 2 pages only (cost control)
result = extractor.extract_first_pages(
    Path("/path/to/scanned_paper.pdf"),
    pages=[0, 1]  # 0-based indexing
)

print(f"Extracted text: {result['text']}")
print(f"Confidence: {result['confidence']}")
print(f"Cost: ${result['cost']:.4f}")
print(f"Pages processed: {result['pages_processed']}")
```

## Cost Management

### Pricing Information

- **Current Rate**: $0.0015 per page processed
- **Hard Limit**: First 2 pages only per document
- **Monthly Budget**: Recommend $50-100 for typical research workloads

### Cost Controls Built-in

1. **Page Limit**: Hardcoded 2-page maximum per document
2. **Cost Tracking**: Automatic tracking to the penny
3. **Fallback Priority**: Only used when other methods fail
4. **Usage Monitoring**: Detailed cost reporting

### Example Cost Calculations

```python
# Cost examples:
# - 100 papers × 2 pages × $0.0015 = $0.30
# - 1000 papers × 2 pages × $0.0015 = $3.00
# - 10000 papers × 2 pages × $0.0015 = $30.00

# Check costs after processing
cost_summary = processor.get_cost_summary()
print(f"Google Vision costs: ${cost_summary['by_extractor']['google_vision']:.4f}")
print(f"Total operations: {cost_summary['operation_counts']['affiliation_extraction']}")
```

## Troubleshooting

### Authentication Errors

```bash
# Verify credentials file exists and is readable
ls -la ~/google-cloud-credentials.json

# Test authentication
gcloud auth activate-service-account --key-file=~/google-cloud-credentials.json
gcloud auth list
```

### API Quota Issues

```bash
# Check quota usage
gcloud logging read "resource.type=cloud_vision" --limit=10

# Monitor in Console:
# https://console.cloud.google.com/apis/api/vision.googleapis.com/quotas
```

### Permission Issues

```bash
# Verify service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:pdf-vision-processor@$PROJECT_ID.iam.gserviceaccount.com"
```

### Common Error Messages

**"DefaultCredentialsError"**
- Ensure `GOOGLE_APPLICATION_CREDENTIALS` environment variable is set
- Verify credentials file path is correct and accessible

**"PermissionDenied"**
- Check that Cloud Vision API is enabled
- Verify service account has `roles/cloudvision.admin` role

**"QuotaExceeded"**
- Check API quotas in Google Cloud Console
- Consider requesting quota increase if needed

## Security Best Practices

1. **Credential Storage**
   - Store credentials file outside of version control
   - Use restricted file permissions (600)
   - Consider using Google Cloud Secret Manager for production

2. **Service Account Permissions**
   - Use least-privilege principle
   - Regularly rotate service account keys
   - Monitor service account usage

3. **Cost Controls**
   - Set up billing alerts in Google Cloud Console
   - Monitor usage regularly
   - Implement application-level budgets

## Integration with PDF Processing Pipeline

The Google Cloud Vision extractor is designed to work as part of a multi-tier extraction strategy:

1. **Level 0**: PyMuPDF (free, fast, works for most PDFs)
2. **Level 1**: GROBID (free, academic-focused)
3. **Level 2**: EasyOCR (free, local OCR)
4. **Level 3**: Google Cloud Vision (paid, high-quality OCR fallback)

This ensures cost-effective processing while maintaining high success rates for difficult documents.

## Monitoring and Optimization

### Usage Analytics

```python
# Get detailed cost breakdown
cost_summary = processor.get_cost_summary()

print("=== Google Cloud Vision Usage ===")
print(f"Total cost: ${cost_summary['total_cost']:.4f}")
print(f"Operations: {cost_summary['total_operations']}")
print(f"Average cost per operation: ${cost_summary['average_cost_per_operation']:.4f}")

# Recent operations
recent_ops = processor.cost_tracker.get_recent_operations(limit=5)
for op in recent_ops:
    print(f"{op['timestamp']}: {op['operation']} - ${op['cost']:.4f}")
```

### Performance Optimization

- **Batch Processing**: Process multiple papers in batches to amortize setup costs
- **Smart Filtering**: Use other extractors first to avoid unnecessary Vision API calls
- **Quality Thresholds**: Set confidence thresholds to retry with different extractors
- **Caching**: Consider caching results for repeated processing of the same documents

## Support and Resources

- [Google Cloud Vision Documentation](https://cloud.google.com/vision/docs)
- [Python Client Library](https://googleapis.dev/python/vision/latest/)
- [Pricing Calculator](https://cloud.google.com/products/calculator)
- [API Quotas and Limits](https://cloud.google.com/vision/quotas)