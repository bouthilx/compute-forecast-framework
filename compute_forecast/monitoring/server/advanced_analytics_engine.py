"""
Advanced Analytics Engine for Issue #14 - Create Advanced Analytics Dashboard.
Provides real-time analytics, historical trend analysis, performance analytics,
and predictive analytics for the paper collection system.
"""

import time
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import threading
from scipy import stats
from sklearn.linear_model import LinearRegression
import warnings

from .dashboard_metrics import SystemMetrics

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsTimeWindow:
    """Time window for analytics calculations"""

    start_time: datetime
    end_time: datetime
    duration_hours: float

    @classmethod
    def last_hours(cls, hours: int) -> "AnalyticsTimeWindow":
        """Create time window for last N hours"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        return cls(start_time, end_time, hours)

    @classmethod
    def last_days(cls, days: int) -> "AnalyticsTimeWindow":
        """Create time window for last N days"""
        return cls.last_hours(days * 24)


@dataclass
class TrendAnalysis:
    """Trend analysis results"""

    metric_name: str
    time_window: AnalyticsTimeWindow
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0.0 to 1.0
    slope: float
    r_squared: float
    confidence_interval: Tuple[float, float]
    prediction_next_hour: Optional[float] = None
    prediction_confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "metric_name": self.metric_name,
            "time_window": {
                "start_time": self.time_window.start_time.isoformat(),
                "end_time": self.time_window.end_time.isoformat(),
                "duration_hours": self.time_window.duration_hours,
            },
            "trend_direction": self.trend_direction,
            "trend_strength": self.trend_strength,
            "slope": self.slope,
            "r_squared": self.r_squared,
            "confidence_interval": self.confidence_interval,
            "prediction_next_hour": self.prediction_next_hour,
            "prediction_confidence": self.prediction_confidence,
        }


@dataclass
class PerformanceAnalytics:
    """Performance analytics results"""

    metric_name: str
    current_value: float
    baseline_value: float
    percentile_rank: float  # 0.0 to 100.0
    performance_score: float  # 0.0 to 100.0
    efficiency_rating: str  # "excellent", "good", "fair", "poor"
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "percentile_rank": self.percentile_rank,
            "performance_score": self.performance_score,
            "efficiency_rating": self.efficiency_rating,
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
        }


@dataclass
class PredictiveAnalytics:
    """Predictive analytics results"""

    metric_name: str
    current_value: float
    predicted_values: Dict[str, float]  # time_horizon -> predicted_value
    confidence_intervals: Dict[
        str, Tuple[float, float]
    ]  # time_horizon -> (lower, upper)
    forecast_accuracy: float  # 0.0 to 1.0
    model_type: str
    factors_influencing: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "predicted_values": self.predicted_values,
            "confidence_intervals": {
                k: list(v) for k, v in self.confidence_intervals.items()
            },
            "forecast_accuracy": self.forecast_accuracy,
            "model_type": self.model_type,
            "factors_influencing": self.factors_influencing,
        }


@dataclass
class AnalyticsSummary:
    """Overall analytics summary"""

    timestamp: datetime
    collection_health_score: float  # 0.0 to 100.0
    system_efficiency_score: float  # 0.0 to 100.0
    predicted_completion_time: Optional[datetime] = None
    critical_insights: List[str] = field(default_factory=list)
    performance_trends: Dict[str, str] = field(default_factory=dict)  # metric -> trend
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "collection_health_score": self.collection_health_score,
            "system_efficiency_score": self.system_efficiency_score,
            "predicted_completion_time": self.predicted_completion_time.isoformat()
            if self.predicted_completion_time
            else None,
            "critical_insights": self.critical_insights,
            "performance_trends": self.performance_trends,
            "recommendations": self.recommendations,
        }


class AdvancedAnalyticsEngine:
    """
    Advanced analytics engine providing real-time analytics, trend analysis,
    performance analytics, and predictive modeling for paper collection.
    """

    def __init__(self, max_history_size: int = 10000):
        self.max_history_size = max_history_size

        # Historical data storage
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.analytics_cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}

        # Performance baselines
        self.performance_baselines = {
            "papers_per_minute": 20.0,
            "api_success_rate": 0.95,
            "memory_usage_percent": 70.0,
            "cpu_usage_percent": 60.0,
            "response_time_ms": 2000.0,
        }

        # Threading
        self._lock = threading.RLock()
        self._analytics_thread: Optional[threading.Thread] = None
        self._running = False

        # Configuration
        self.cache_duration_seconds = 60  # Cache analytics for 1 minute
        self.trend_analysis_window_hours = 6
        self.prediction_horizons = ["1h", "6h", "24h"]

        logger.info("AdvancedAnalyticsEngine initialized")

    def start(self) -> None:
        """Start analytics processing"""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._analytics_thread = threading.Thread(
                target=self._analytics_loop, daemon=True, name="AdvancedAnalytics"
            )
            self._analytics_thread.start()

        logger.info("Advanced analytics engine started")

    def stop(self) -> None:
        """Stop analytics processing"""
        with self._lock:
            self._running = False

        if self._analytics_thread:
            self._analytics_thread.join(timeout=5.0)

        logger.info("Advanced analytics engine stopped")

    def add_metrics_data(self, metrics: SystemMetrics) -> None:
        """Add new metrics data for analysis"""
        with self._lock:
            self.metrics_history.append(metrics)

            # Invalidate cache when new data arrives
            self._invalidate_cache()

    def get_trend_analysis(
        self, metric_name: str, time_window: Optional[AnalyticsTimeWindow] = None
    ) -> Optional[TrendAnalysis]:
        """
        Analyze trends for specified metric.

        Args:
            metric_name: Name of metric to analyze
            time_window: Time window for analysis (default: last 6 hours)
        """
        if time_window is None:
            time_window = AnalyticsTimeWindow.last_hours(
                self.trend_analysis_window_hours
            )

        cache_key = (
            f"trend_{metric_name}_{time_window.start_time}_{time_window.end_time}"
        )

        # Check cache
        if self._is_cached(cache_key):
            cached_result = self.analytics_cache[cache_key]
            return cached_result if isinstance(cached_result, TrendAnalysis) else None

        try:
            # Extract time series data
            time_series = self._extract_time_series(metric_name, time_window)

            if len(time_series) < 3:
                logger.debug(f"Insufficient data for trend analysis of {metric_name}")
                return None

            # Perform trend analysis
            trend_analysis = self._analyze_trend(metric_name, time_series, time_window)

            # Cache result
            self._cache_result(cache_key, trend_analysis)

            return trend_analysis

        except Exception as e:
            logger.error(f"Error in trend analysis for {metric_name}: {e}")
            return None

    def get_performance_analytics(
        self, metric_name: str
    ) -> Optional[PerformanceAnalytics]:
        """
        Analyze performance for specified metric.

        Args:
            metric_name: Name of metric to analyze
        """
        cache_key = f"performance_{metric_name}"

        # Check cache
        if self._is_cached(cache_key):
            cached_result = self.analytics_cache[cache_key]
            return (
                cached_result
                if isinstance(cached_result, PerformanceAnalytics)
                else None
            )

        try:
            # Get current and historical values
            current_value = self._get_current_metric_value(metric_name)
            if current_value is None:
                return None

            historical_values = self._get_historical_metric_values(
                metric_name, hours=24
            )

            if len(historical_values) < 5:
                logger.debug(
                    f"Insufficient historical data for performance analysis of {metric_name}"
                )
                return None

            # Perform performance analysis
            performance_analytics = self._analyze_performance(
                metric_name, current_value, historical_values
            )

            # Cache result
            self._cache_result(cache_key, performance_analytics)

            return performance_analytics

        except Exception as e:
            logger.error(f"Error in performance analysis for {metric_name}: {e}")
            return None

    def get_predictive_analytics(
        self, metric_name: str
    ) -> Optional[PredictiveAnalytics]:
        """
        Generate predictive analytics for specified metric.

        Args:
            metric_name: Name of metric to predict
        """
        cache_key = f"predictive_{metric_name}"

        # Check cache
        if self._is_cached(cache_key):
            cached_result = self.analytics_cache[cache_key]
            return (
                cached_result
                if isinstance(cached_result, PredictiveAnalytics)
                else None
            )

        try:
            # Get historical data
            time_series = self._extract_time_series(
                metric_name, AnalyticsTimeWindow.last_hours(24)
            )

            if len(time_series) < 10:
                logger.debug(
                    f"Insufficient data for predictive analysis of {metric_name}"
                )
                return None

            # Perform predictive analysis
            predictive_analytics = self._analyze_predictions(metric_name, time_series)

            # Cache result
            self._cache_result(cache_key, predictive_analytics)

            return predictive_analytics

        except Exception as e:
            logger.error(f"Error in predictive analysis for {metric_name}: {e}")
            return None

    def get_comprehensive_summary(self) -> AnalyticsSummary:
        """Generate comprehensive analytics summary"""
        cache_key = "comprehensive_summary"

        # Check cache
        if self._is_cached(cache_key):
            cached_result = self.analytics_cache[cache_key]
            return (
                cached_result
                if isinstance(cached_result, AnalyticsSummary)
                else self._generate_comprehensive_summary()
            )

        try:
            summary = self._generate_comprehensive_summary()

            # Cache result
            self._cache_result(cache_key, summary)

            return summary

        except Exception as e:
            logger.error(f"Error generating comprehensive summary: {e}")
            return AnalyticsSummary(
                timestamp=datetime.now(),
                collection_health_score=50.0,
                system_efficiency_score=50.0,
                critical_insights=["Unable to generate analytics due to error"],
                recommendations=["Check system logs for errors"],
            )

    def get_custom_analytics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate custom analytics based on configuration"""
        try:
            results: Dict[str, Any] = {}

            # Custom metric calculations
            if "custom_metrics" in config:
                for metric_config in config["custom_metrics"]:
                    metric_name = metric_config["name"]
                    calculation = metric_config["calculation"]

                    result = self._calculate_custom_metric(calculation)
                    results[metric_name] = result

            # Custom time window analysis
            if "time_windows" in config:
                for window_config in config["time_windows"]:
                    window_name = window_config["name"]
                    hours = window_config["hours"]
                    metrics = window_config.get("metrics", [])

                    window_results: Dict[str, Any] = {}
                    for metric in metrics:
                        trend = self.get_trend_analysis(
                            metric, AnalyticsTimeWindow.last_hours(hours)
                        )
                        if trend:
                            window_results[metric] = trend.to_dict()

                    results[window_name] = window_results

            return results

        except Exception as e:
            logger.error(f"Error in custom analytics: {e}")
            return {"error": str(e)}

    def _extract_time_series(
        self, metric_name: str, time_window: AnalyticsTimeWindow
    ) -> List[Tuple[datetime, float]]:
        """Extract time series data for metric within time window"""
        time_series = []

        with self._lock:
            for metrics in self.metrics_history:
                if time_window.start_time <= metrics.timestamp <= time_window.end_time:
                    value = self._get_metric_value_from_object(metrics, metric_name)
                    if value is not None:
                        time_series.append((metrics.timestamp, value))

        # Sort by timestamp
        time_series.sort(key=lambda x: x[0])
        return time_series

    def _analyze_trend(
        self,
        metric_name: str,
        time_series: List[Tuple[datetime, float]],
        time_window: AnalyticsTimeWindow,
    ) -> TrendAnalysis:
        """Analyze trend in time series data"""
        if len(time_series) < 3:
            raise ValueError("Insufficient data for trend analysis")

        # Convert to numpy arrays
        timestamps = np.array([t.timestamp() for t, v in time_series])
        values = np.array([v for t, v in time_series])

        # Normalize timestamps to hours from start
        time_hours = (timestamps - timestamps[0]) / 3600

        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            time_hours, values
        )

        # Determine trend direction and strength
        r_squared = r_value**2

        if abs(slope) < std_err:
            trend_direction = "stable"
            trend_strength = 1.0 - abs(slope) / (abs(slope) + std_err)
        elif slope > 0:
            trend_direction = "increasing"
            trend_strength = min(
                1.0, abs(slope) / values.std() if values.std() > 0 else 0.5
            )
        else:
            trend_direction = "decreasing"
            trend_strength = min(
                1.0, abs(slope) / values.std() if values.std() > 0 else 0.5
            )

        # Confidence interval
        confidence_interval = (slope - 1.96 * std_err, slope + 1.96 * std_err)

        # Prediction for next hour
        next_hour_time = time_hours[-1] + 1
        prediction_next_hour = slope * next_hour_time + intercept
        prediction_confidence = r_squared

        return TrendAnalysis(
            metric_name=metric_name,
            time_window=time_window,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            slope=slope,
            r_squared=r_squared,
            confidence_interval=confidence_interval,
            prediction_next_hour=prediction_next_hour,
            prediction_confidence=prediction_confidence,
        )

    def _analyze_performance(
        self, metric_name: str, current_value: float, historical_values: List[float]
    ) -> PerformanceAnalytics:
        """Analyze performance metrics"""
        baseline_value = float(
            self.performance_baselines.get(
                metric_name, float(np.median(historical_values))
            )
        )

        # Calculate percentile rank
        sorted_values = sorted(historical_values + [current_value])
        percentile_rank = (
            sorted_values.index(current_value) / len(sorted_values)
        ) * 100

        # Calculate performance score
        if metric_name in ["papers_per_minute", "api_success_rate"]:
            # Higher is better
            performance_score = float(
                min(100.0, (current_value / baseline_value) * 100)
            )
        else:
            # Lower is better (memory, CPU, response time)
            performance_score = float(
                max(0.0, 100.0 - ((current_value / baseline_value) * 50))
            )

        # Determine efficiency rating
        if performance_score >= 90:
            efficiency_rating = "excellent"
        elif performance_score >= 75:
            efficiency_rating = "good"
        elif performance_score >= 50:
            efficiency_rating = "fair"
        else:
            efficiency_rating = "poor"

        # Identify bottlenecks and recommendations
        bottlenecks, recommendations = self._identify_bottlenecks_and_recommendations(
            metric_name, current_value, performance_score
        )

        return PerformanceAnalytics(
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            percentile_rank=percentile_rank,
            performance_score=performance_score,
            efficiency_rating=efficiency_rating,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

    def _analyze_predictions(
        self, metric_name: str, time_series: List[Tuple[datetime, float]]
    ) -> PredictiveAnalytics:
        """Generate predictive analytics"""
        if len(time_series) < 10:
            raise ValueError("Insufficient data for prediction")

        # Prepare data
        timestamps = np.array([t.timestamp() for t, v in time_series])
        values = np.array([v for t, v in time_series])
        time_hours = (timestamps - timestamps[0]) / 3600

        # Train linear regression model
        X = time_hours.reshape(-1, 1)
        y = values

        model = LinearRegression()
        model.fit(X, y)

        # Calculate forecast accuracy (R-squared)
        forecast_accuracy = model.score(X, y)

        # Generate predictions
        predicted_values = {}
        confidence_intervals = {}

        for horizon in self.prediction_horizons:
            hours_ahead = int(horizon[:-1])  # Extract number from '1h', '6h', etc.
            future_time = time_hours[-1] + hours_ahead

            prediction = model.predict([[future_time]])[0]
            predicted_values[horizon] = prediction

            # Simple confidence interval based on historical variance
            residuals = y - model.predict(X)
            std_error = np.std(residuals)
            confidence_intervals[horizon] = (
                prediction - 1.96 * std_error,
                prediction + 1.96 * std_error,
            )

        # Identify influencing factors
        factors_influencing = self._identify_influencing_factors(metric_name)

        return PredictiveAnalytics(
            metric_name=metric_name,
            current_value=values[-1],
            predicted_values=predicted_values,
            confidence_intervals=confidence_intervals,
            forecast_accuracy=forecast_accuracy,
            model_type="linear_regression",
            factors_influencing=factors_influencing,
        )

    def _generate_comprehensive_summary(self) -> AnalyticsSummary:
        """Generate comprehensive analytics summary"""
        current_time = datetime.now()

        # Calculate health scores
        collection_health_score = self._calculate_collection_health_score()
        system_efficiency_score = self._calculate_system_efficiency_score()

        # Get critical insights
        critical_insights = self._generate_critical_insights()

        # Get performance trends
        performance_trends = {}
        key_metrics = ["papers_per_minute", "memory_usage_percent", "cpu_usage_percent"]

        for metric in key_metrics:
            trend = self.get_trend_analysis(metric)
            if trend:
                performance_trends[metric] = trend.trend_direction

        # Generate recommendations
        recommendations = self._generate_recommendations(
            collection_health_score, system_efficiency_score, performance_trends
        )

        # Predict completion time
        predicted_completion_time = self._predict_completion_time()

        return AnalyticsSummary(
            timestamp=current_time,
            collection_health_score=collection_health_score,
            system_efficiency_score=system_efficiency_score,
            predicted_completion_time=predicted_completion_time,
            critical_insights=critical_insights,
            performance_trends=performance_trends,
            recommendations=recommendations,
        )

    def _calculate_collection_health_score(self) -> float:
        """Calculate overall collection health score"""
        try:
            current_metrics = self._get_latest_metrics()
            if not current_metrics:
                return 50.0

            scores = []

            # Collection rate score
            rate = current_metrics.collection_progress.papers_per_minute
            rate_score = min(100, (rate / 20.0) * 100) if rate > 0 else 0
            scores.append(float(rate_score))

            # API health score
            api_scores = []
            for api_name, api_metrics in current_metrics.api_metrics.items():
                api_score = (
                    api_metrics.success_rate * 100
                    if hasattr(api_metrics, "success_rate")
                    else 100
                )
                api_scores.append(api_score)

            if api_scores:
                scores.append(float(np.mean(api_scores)))

            # Processing score
            if hasattr(
                current_metrics.processing_metrics, "processing_errors"
            ) and hasattr(current_metrics.processing_metrics, "papers_processed"):
                if current_metrics.processing_metrics.papers_processed > 0:
                    error_rate = (
                        current_metrics.processing_metrics.processing_errors
                        / current_metrics.processing_metrics.papers_processed
                    )
                    processing_score = max(
                        0, 100 - (error_rate * 1000)
                    )  # Scale error rate
                    scores.append(processing_score)

            return float(np.mean(scores)) if scores else 50.0

        except Exception as e:
            logger.debug(f"Error calculating collection health score: {e}")
            return 50.0

    def _calculate_system_efficiency_score(self) -> float:
        """Calculate system efficiency score"""
        try:
            current_metrics = self._get_latest_metrics()
            if not current_metrics:
                return 50.0

            scores = []

            # Memory efficiency (lower is better)
            memory_usage = current_metrics.system_metrics.memory_usage_percentage
            memory_score = max(0, 100 - memory_usage) if memory_usage > 0 else 100
            scores.append(memory_score)

            # CPU efficiency (lower is better)
            cpu_usage = current_metrics.system_metrics.cpu_usage_percentage
            cpu_score = max(0, 100 - cpu_usage) if cpu_usage > 0 else 100
            scores.append(cpu_score)

            # Network efficiency (placeholder - would need actual metrics)
            scores.append(85.0)  # Assume good network efficiency

            return float(np.mean(scores))

        except Exception as e:
            logger.debug(f"Error calculating system efficiency score: {e}")
            return 50.0

    def _generate_critical_insights(self) -> List[str]:
        """Generate critical insights based on current analytics"""
        insights = []

        try:
            # Check collection rate trends
            rate_trend = self.get_trend_analysis("papers_per_minute")
            if (
                rate_trend
                and rate_trend.trend_direction == "decreasing"
                and rate_trend.trend_strength > 0.7
            ):
                insights.append(
                    f"Collection rate is declining significantly ({rate_trend.slope:.2f} papers/min/hour)"
                )

            # Check system resource trends
            memory_trend = self.get_trend_analysis("memory_usage_percent")
            if (
                memory_trend
                and memory_trend.trend_direction == "increasing"
                and memory_trend.trend_strength > 0.8
            ):
                insights.append(
                    "Memory usage is increasing rapidly - potential memory leak detected"
                )

            # Check API performance
            current_metrics = self._get_latest_metrics()
            if current_metrics:
                for api_name, api_metrics in current_metrics.api_metrics.items():
                    if (
                        hasattr(api_metrics, "success_rate")
                        and api_metrics.success_rate < 0.8
                    ):
                        insights.append(
                            f"API {api_name} success rate is critically low ({api_metrics.success_rate:.1%})"
                        )

            if not insights:
                insights.append("System is operating within normal parameters")

        except Exception as e:
            logger.debug(f"Error generating critical insights: {e}")
            insights.append("Unable to generate insights due to insufficient data")

        return insights

    def _generate_recommendations(
        self, health_score: float, efficiency_score: float, trends: Dict[str, str]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if health_score < 70:
            recommendations.append(
                "Consider investigating collection bottlenecks or API issues"
            )

        if efficiency_score < 60:
            recommendations.append(
                "System resources are under stress - consider scaling up"
            )

        if (
            "papers_per_minute" in trends
            and trends["papers_per_minute"] == "decreasing"
        ):
            recommendations.append(
                "Collection rate is declining - check for API rate limits or processing delays"
            )

        if (
            "memory_usage_percent" in trends
            and trends["memory_usage_percent"] == "increasing"
        ):
            recommendations.append(
                "Memory usage is trending upward - monitor for memory leaks"
            )

        if not recommendations:
            recommendations.append("System is performing well - continue monitoring")

        return recommendations

    def _predict_completion_time(self) -> Optional[datetime]:
        """Predict when current collection will complete"""
        try:
            current_metrics = self._get_latest_metrics()
            if not current_metrics:
                return None

            # Get collection progress
            progress = current_metrics.collection_progress
            if not hasattr(progress, "venues_remaining") or not hasattr(
                progress, "papers_per_minute"
            ):
                return None

            if progress.papers_per_minute <= 0 or progress.venues_remaining <= 0:
                return None

            # Estimate papers per venue (rough estimate)
            papers_per_venue = 50  # Average papers per venue
            remaining_papers = progress.venues_remaining * papers_per_venue

            # Calculate time to completion
            hours_remaining = remaining_papers / (progress.papers_per_minute * 60)

            return datetime.now() + timedelta(hours=hours_remaining)

        except Exception as e:
            logger.debug(f"Error predicting completion time: {e}")
            return None

    def _identify_bottlenecks_and_recommendations(
        self, metric_name: str, current_value: float, performance_score: float
    ) -> Tuple[List[str], List[str]]:
        """Identify bottlenecks and generate recommendations"""
        bottlenecks = []
        recommendations = []

        if metric_name == "papers_per_minute" and performance_score < 60:
            bottlenecks.append("Low collection rate")
            recommendations.append(
                "Check API rate limits and processing pipeline efficiency"
            )

        if metric_name == "memory_usage_percent" and current_value > 80:
            bottlenecks.append("High memory usage")
            recommendations.append(
                "Consider increasing memory allocation or optimizing data structures"
            )

        if metric_name == "cpu_usage_percent" and current_value > 85:
            bottlenecks.append("High CPU usage")
            recommendations.append(
                "Consider parallel processing optimization or CPU scaling"
            )

        return bottlenecks, recommendations

    def _identify_influencing_factors(self, metric_name: str) -> List[str]:
        """Identify factors that influence the metric"""
        factors_map = {
            "papers_per_minute": [
                "API response time",
                "Processing efficiency",
                "Network bandwidth",
            ],
            "memory_usage_percent": [
                "Dataset size",
                "Processing algorithms",
                "Garbage collection",
            ],
            "cpu_usage_percent": [
                "Concurrent processes",
                "Algorithm complexity",
                "I/O operations",
            ],
            "api_success_rate": ["Network stability", "API rate limits", "Server load"],
        }

        return factors_map.get(
            metric_name, ["System load", "Network conditions", "Resource availability"]
        )

    def _calculate_custom_metric(self, calculation: str) -> float:
        """Calculate custom metric based on expression"""
        try:
            # This is a simplified implementation
            # In production, would need proper expression parsing and security
            current_metrics = self._get_latest_metrics()
            if not current_metrics:
                return 0.0

            # Safe evaluation with limited scope
            safe_dict = {
                "papers_per_minute": current_metrics.collection_progress.papers_per_minute,
                "memory_usage": current_metrics.system_metrics.memory_usage_percentage,
                "cpu_usage": current_metrics.system_metrics.cpu_usage_percentage,
            }

            result = eval(calculation, {"__builtins__": {}}, safe_dict)
            return float(result)

        except Exception as e:
            logger.error(f"Error calculating custom metric: {e}")
            return 0.0

    def _get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get latest metrics from history"""
        with self._lock:
            return self.metrics_history[-1] if self.metrics_history else None

    def _get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value for specified metric"""
        latest_metrics = self._get_latest_metrics()
        if not latest_metrics:
            return None

        return self._get_metric_value_from_object(latest_metrics, metric_name)

    def _get_historical_metric_values(
        self, metric_name: str, hours: int = 24
    ) -> List[float]:
        """Get historical values for metric"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        values = []

        with self._lock:
            for metrics in self.metrics_history:
                if metrics.timestamp >= cutoff_time:
                    value = self._get_metric_value_from_object(metrics, metric_name)
                    if value is not None:
                        values.append(value)

        return values

    def _get_metric_value_from_object(
        self, metrics: SystemMetrics, metric_name: str
    ) -> Optional[float]:
        """Extract metric value from SystemMetrics object"""
        try:
            if metric_name == "papers_per_minute":
                return metrics.collection_progress.papers_per_minute
            elif metric_name == "memory_usage_percent":
                return float(metrics.system_metrics.memory_usage_percentage)
            elif metric_name == "cpu_usage_percent":
                return float(metrics.system_metrics.cpu_usage_percentage)
            elif metric_name == "total_papers":
                return float(metrics.collection_progress.papers_collected)
            elif metric_name == "venues_completed":
                return float(
                    getattr(metrics.collection_progress, "venues_completed", 0)
                )
            elif metric_name == "api_success_rate":
                # Average success rate across all APIs
                rates = []
                for api_metrics in metrics.api_metrics.values():
                    if hasattr(api_metrics, "success_rate"):
                        rates.append(api_metrics.success_rate)
                return float(np.mean(rates)) if rates else None
            else:
                return None

        except (AttributeError, KeyError):
            return None

    def _is_cached(self, cache_key: str) -> bool:
        """Check if result is cached and still valid"""
        if cache_key not in self.analytics_cache:
            return False

        if cache_key not in self.cache_ttl:
            return False

        return datetime.now() < self.cache_ttl[cache_key]

    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache analysis result"""
        self.analytics_cache[cache_key] = result
        self.cache_ttl[cache_key] = datetime.now() + timedelta(
            seconds=self.cache_duration_seconds
        )

    def _invalidate_cache(self) -> None:
        """Invalidate expired cache entries"""
        current_time = datetime.now()
        expired_keys = [
            key
            for key, expiry_time in self.cache_ttl.items()
            if current_time >= expiry_time
        ]

        for key in expired_keys:
            self.analytics_cache.pop(key, None)
            self.cache_ttl.pop(key, None)

    def _analytics_loop(self) -> None:
        """Background analytics processing loop"""
        while self._running:
            try:
                # Periodic cache cleanup
                self._invalidate_cache()

                # Pre-compute common analytics
                if self.metrics_history:
                    self.get_comprehensive_summary()

                time.sleep(60)  # Run every minute

            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                time.sleep(10)  # Short delay on error
