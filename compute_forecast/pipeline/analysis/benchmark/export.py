"""CSV export functionality for benchmark extraction results."""

import csv
from typing import List

from compute_forecast.pipeline.analysis.benchmark.models import (
    ExtractionBatch,
    BenchmarkExport,
)


class BenchmarkCSVExporter:
    """Export benchmark extraction results to CSV format."""

    def __init__(self):
        self.csv_headers = [
            "paper_id",
            "title",
            "year",
            "domain",
            "venue",
            "gpu_hours",
            "gpu_type",
            "gpu_count",
            "training_days",
            "parameters_millions",
            "dataset_size_gb",
            "extraction_confidence",
            "is_sota",
            "benchmark_datasets",
        ]

    def export_batches_to_csv(
        self, batches: List[ExtractionBatch], output_path: str
    ) -> None:
        """Export multiple extraction batches to CSV file."""
        with open(output_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.csv_headers)
            writer.writeheader()

            for batch in batches:
                for paper in batch.papers:
                    export = self._paper_to_export(paper)
                    writer.writerow(export.to_csv_row())

    def export_to_dataframe(self, batches: List[ExtractionBatch]):
        """Export to pandas DataFrame for analysis."""
        import pandas as pd

        rows = []
        for batch in batches:
            for paper in batch.papers:
                export = self._paper_to_export(paper)
                rows.append(export.to_csv_row())

        return pd.DataFrame(rows)

    def _paper_to_export(self, benchmark_paper) -> BenchmarkExport:
        """Convert BenchmarkPaper to BenchmarkExport."""
        paper = benchmark_paper.paper
        comp = benchmark_paper.computational_requirements

        # Extract metrics from resource_metrics if available
        resource_metrics = comp.resource_metrics if comp.resource_metrics else {}

        return BenchmarkExport(
            paper_id=paper.paper_id or "unknown",
            title=paper.title,
            year=paper.year,
            domain=benchmark_paper.domain,
            venue=paper.venue,
            gpu_hours=resource_metrics.get("gpu_hours"),
            gpu_type=resource_metrics.get("gpu_type"),
            gpu_count=resource_metrics.get("gpu_count"),
            training_days=resource_metrics.get("training_time_days"),
            parameters_millions=resource_metrics.get("parameters", 0) / 1_000_000
            if resource_metrics.get("parameters")
            else None,
            dataset_size_gb=resource_metrics.get("dataset_size"),
            extraction_confidence=benchmark_paper.extraction_confidence,
            is_sota=benchmark_paper.is_sota,
            benchmark_datasets=benchmark_paper.benchmark_datasets,
        )
