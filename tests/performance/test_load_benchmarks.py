"""Performance benchmarks for n8n deployment."""
import asyncio
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Tuple

import aiohttp
import boto3
import pytest


@pytest.mark.performance
@pytest.mark.slow
class TestLoadBenchmarks:
    """Load testing benchmarks for n8n deployment."""

    @pytest.fixture
    def n8n_base_url(self):
        """Get n8n base URL from environment or configuration."""
        # This would be set based on your deployment
        return "https://n8n.example.com"

    @pytest.fixture
    def api_credentials(self):
        """Get API credentials for testing."""
        return {"username": "test_user", "password": "test_password"}

    async def _make_webhook_request(
        self, session: aiohttp.ClientSession, webhook_url: str, payload: dict
    ) -> Tuple[int, float]:
        """Make async webhook request and measure response time."""
        start_time = time.time()
        try:
            async with session.post(webhook_url, json=payload) as response:
                status = response.status
                await response.text()
                response_time = time.time() - start_time
                return status, response_time
        except Exception as e:
            return 500, time.time() - start_time

    async def _run_webhook_load_test(
        self, webhook_url: str, num_requests: int, concurrent_requests: int
    ) -> Dict[str, any]:
        """Run webhook load test with specified concurrency."""
        results = []
        payload = {
            "test": "data",
            "timestamp": datetime.now().isoformat(),
            "request_id": None,
        }

        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_requests):
                payload["request_id"] = f"test-{i}"
                task = self._make_webhook_request(session, webhook_url, payload.copy())
                tasks.append(task)

                # Control concurrency
                if len(tasks) >= concurrent_requests:
                    batch_results = await asyncio.gather(*tasks)
                    results.extend(batch_results)
                    tasks = []

            # Process remaining tasks
            if tasks:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)

        # Calculate statistics
        status_codes = [r[0] for r in results]
        response_times = [r[1] for r in results]

        return {
            "total_requests": num_requests,
            "concurrent_requests": concurrent_requests,
            "success_count": sum(1 for s in status_codes if 200 <= s < 300),
            "error_count": sum(1 for s in status_codes if s >= 400),
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[
                18
            ],  # 95th percentile
            "p99_response_time": statistics.quantiles(response_times, n=100)[
                98
            ],  # 99th percentile
            "requests_per_second": num_requests / sum(response_times),
        }

    @pytest.mark.asyncio
    async def test_webhook_performance_baseline(self, n8n_base_url):
        """Test webhook performance baseline."""
        webhook_url = f"{n8n_base_url}/webhook/test-performance"

        # Baseline test - 100 requests, 10 concurrent
        results = await self._run_webhook_load_test(webhook_url, 100, 10)

        # Assert baseline performance
        assert results["success_count"] >= 95, "Success rate below 95%"
        assert (
            results["avg_response_time"] < 1.0
        ), "Average response time above 1 second"
        assert results["p95_response_time"] < 2.0, "95th percentile above 2 seconds"

        print(f"Baseline Performance Results: {json.dumps(results, indent=2)}")

    @pytest.mark.asyncio
    async def test_webhook_performance_under_load(self, n8n_base_url):
        """Test webhook performance under heavy load."""
        webhook_url = f"{n8n_base_url}/webhook/test-performance"

        # Load test - 1000 requests, 50 concurrent
        results = await self._run_webhook_load_test(webhook_url, 1000, 50)

        # Assert performance under load
        assert results["success_count"] >= 900, "Success rate below 90% under load"
        assert (
            results["avg_response_time"] < 2.0
        ), "Average response time above 2 seconds under load"
        assert (
            results["p99_response_time"] < 5.0
        ), "99th percentile above 5 seconds under load"

        print(f"Load Test Results: {json.dumps(results, indent=2)}")

    @pytest.mark.asyncio
    async def test_webhook_performance_stress(self, n8n_base_url):
        """Test webhook performance under stress conditions."""
        webhook_url = f"{n8n_base_url}/webhook/test-performance"

        # Stress test - 5000 requests, 200 concurrent
        results = await self._run_webhook_load_test(webhook_url, 5000, 200)

        # More relaxed assertions for stress test
        assert results["success_count"] >= 4000, "Success rate below 80% under stress"
        assert (
            results["avg_response_time"] < 5.0
        ), "Average response time above 5 seconds under stress"

        print(f"Stress Test Results: {json.dumps(results, indent=2)}")

    def test_workflow_execution_performance(self, n8n_base_url, api_credentials):
        """Test workflow execution performance."""
        # This would test actual workflow execution via API
        # Placeholder for workflow execution tests
        pass

    def test_database_query_performance(self):
        """Test database query performance for n8n operations."""
        # Connect to database (if accessible)
        # Run typical n8n queries and measure performance
        pass

    def test_efs_throughput_performance(self):
        """Test EFS throughput for n8n file operations."""
        # Mount EFS and test file operations
        # Measure read/write throughput
        pass

    def test_scaling_performance(self):
        """Test auto-scaling performance."""
        ecs = boto3.client("ecs")
        cloudwatch = boto3.client("cloudwatch")

        # This would test how quickly the service scales
        # under load and how it affects performance
        pass

    @pytest.mark.asyncio
    async def test_concurrent_workflow_performance(self, n8n_base_url, api_credentials):
        """Test performance with multiple concurrent workflows."""
        # Create multiple test workflows
        # Execute them concurrently
        # Measure execution times and resource usage
        pass

    def test_memory_usage_under_load(self):
        """Test memory usage patterns under load."""
        # Monitor memory usage during load tests
        # Check for memory leaks
        pass

    def test_cpu_usage_patterns(self):
        """Test CPU usage patterns during different operations."""
        # Monitor CPU usage during:
        # - Webhook processing
        # - Workflow execution
        # - Database operations
        pass


@pytest.mark.performance
class TestPerformanceMetrics:
    """Test performance metric collection and baselines."""

    def test_metric_collection_overhead(self):
        """Test overhead of custom metric collection."""
        # Measure performance impact of metric collection
        pass

    def test_logging_performance_impact(self):
        """Test performance impact of logging."""
        # Measure impact of different log levels
        pass

    def test_circuit_breaker_performance(self):
        """Test circuit breaker response times."""
        # Measure circuit breaker check latency
        pass


def generate_performance_report(results: List[Dict]) -> str:
    """Generate performance benchmark report."""
    report = []
    report.append("# n8n AWS Serverless Performance Benchmark Report")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("")

    for test_result in results:
        report.append(f"## {test_result['test_name']}")
        report.append(f"- Total Requests: {test_result['total_requests']}")
        report.append(f"- Success Rate: {test_result['success_rate']}%")
        report.append(
            f"- Average Response Time: {test_result['avg_response_time']:.3f}s"
        )
        report.append(f"- P95 Response Time: {test_result['p95_response_time']:.3f}s")
        report.append(f"- P99 Response Time: {test_result['p99_response_time']:.3f}s")
        report.append(f"- Requests/Second: {test_result['requests_per_second']:.2f}")
        report.append("")

    return "\n".join(report)


class LoadTestScenarios:
    """Predefined load test scenarios."""

    @staticmethod
    def steady_load(duration_minutes: int = 10, requests_per_second: int = 10):
        """Steady load over time."""
        return {
            "type": "steady",
            "duration": duration_minutes * 60,
            "rps": requests_per_second,
        }

    @staticmethod
    def ramp_up(start_rps: int = 1, end_rps: int = 100, duration_minutes: int = 5):
        """Gradual ramp up of load."""
        return {
            "type": "ramp",
            "start_rps": start_rps,
            "end_rps": end_rps,
            "duration": duration_minutes * 60,
        }

    @staticmethod
    def spike_test(
        baseline_rps: int = 10, spike_rps: int = 100, spike_duration: int = 60
    ):
        """Spike test scenario."""
        return {
            "type": "spike",
            "baseline_rps": baseline_rps,
            "spike_rps": spike_rps,
            "spike_duration": spike_duration,
        }
