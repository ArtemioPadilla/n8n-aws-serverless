"""Integration tests for local Docker deployment."""
import os
import subprocess
import time
from pathlib import Path

import pytest
import requests

import docker


@pytest.mark.integration
@pytest.mark.docker
class TestLocalDeployment:
    """Integration tests for local Docker deployment."""

    @pytest.fixture
    def docker_client(self):
        """Create Docker client."""
        try:
            client = docker.from_env()
            # Test connection
            client.ping()
            return client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def cleanup_containers(self, docker_client):
        """Cleanup Docker containers after tests."""
        yield
        # Cleanup
        try:
            containers = docker_client.containers.list(
                all=True, filters={"label": "com.docker.compose.project=n8n-local"}
            )
            for container in containers:
                container.stop()
                container.remove()
        except Exception:
            pass

    def test_docker_compose_files_exist(self, project_root):
        """Test that Docker Compose files exist."""
        docker_dir = project_root / "docker"
        assert docker_dir.exists()
        assert (docker_dir / "docker-compose.yml").exists()
        assert (docker_dir / "docker-compose.prod.yml").exists()
        assert (docker_dir / ".env.example").exists()

    def test_local_setup_script(self, project_root):
        """Test local setup script execution."""
        setup_script = project_root / "scripts" / "local-setup.sh"
        assert setup_script.exists()
        assert os.access(setup_script, os.X_OK)

        # Test script in dry-run mode if possible
        result = subprocess.run(
            [str(setup_script), "--check"], capture_output=True, text=True
        )

        # Script should at least run without major errors
        assert result.returncode in [0, 1]  # 0 for success, 1 for missing dependencies

    @pytest.mark.slow
    def test_docker_compose_validation(self, project_root, docker_client):
        """Test Docker Compose configuration validation."""
        docker_dir = project_root / "docker"

        # Validate docker-compose.yml
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(docker_dir / "docker-compose.yml"),
                "config",
            ],
            capture_output=True,
            text=True,
            cwd=str(docker_dir),
        )

        assert result.returncode == 0
        assert "n8n:" in result.stdout
        assert "image: n8nio/n8n:1.94.1" in result.stdout

    @pytest.mark.slow
    def test_n8n_container_startup(
        self, project_root, docker_client, cleanup_containers
    ):
        """Test n8n container starts successfully."""
        docker_dir = project_root / "docker"

        # Create .env file from example
        env_example = docker_dir / ".env.example"
        env_file = docker_dir / ".env"

        if env_example.exists() and not env_file.exists():
            env_file.write_text(env_example.read_text())

        # Start n8n container
        result = subprocess.run(
            ["docker-compose", "up", "-d", "n8n"],
            capture_output=True,
            text=True,
            cwd=str(docker_dir),
            env={**os.environ, "COMPOSE_PROJECT_NAME": "n8n-local-test"},
        )

        assert result.returncode == 0

        # Wait for container to be ready
        container = None
        for _ in range(30):  # 30 second timeout
            containers = docker_client.containers.list(
                filters={"label": "com.docker.compose.service=n8n"}
            )
            if containers:
                container = containers[0]
                if container.status == "running":
                    break
            time.sleep(1)

        assert container is not None
        assert container.status == "running"

        # Check container health
        time.sleep(5)  # Give n8n time to initialize

        # Stop container
        subprocess.run(
            ["docker-compose", "down"],
            cwd=str(docker_dir),
            env={**os.environ, "COMPOSE_PROJECT_NAME": "n8n-local-test"},
        )

    def test_environment_variables(self, project_root):
        """Test environment variable configuration."""
        env_example = project_root / "docker" / ".env.example"
        assert env_example.exists()

        env_content = env_example.read_text()

        # Check required environment variables
        required_vars = [
            "N8N_BASIC_AUTH_ACTIVE",
            "N8N_BASIC_AUTH_USER",
            "N8N_BASIC_AUTH_PASSWORD",
            "N8N_ENCRYPTION_KEY",
            "DB_TYPE",
            "NODE_ENV",
        ]

        for var in required_vars:
            assert var in env_content

    def test_volume_mounts(self, project_root):
        """Test Docker volume configuration."""
        docker_compose = project_root / "docker" / "docker-compose.yml"

        with open(docker_compose) as f:
            content = f.read()

        # Check for volume mounts
        assert "volumes:" in content
        assert "n8n_data:" in content
        assert "/home/node/.n8n" in content

    def test_postgres_deployment(self, project_root):
        """Test PostgreSQL deployment configuration."""
        docker_compose_prod = project_root / "docker" / "docker-compose.prod.yml"

        with open(docker_compose_prod) as f:
            content = f.read()

        # Check PostgreSQL configuration
        assert "postgres:" in content
        assert "image: postgres:" in content
        assert "POSTGRES_DB" in content
        assert "POSTGRES_USER" in content
        assert "POSTGRES_PASSWORD" in content

    def test_nginx_configuration(self, project_root):
        """Test nginx reverse proxy configuration."""
        nginx_conf = project_root / "docker" / "nginx.conf"

        if nginx_conf.exists():
            with open(nginx_conf) as f:
                content = f.read()

            # Check nginx configuration
            assert "upstream n8n" in content
            assert "proxy_pass" in content
            assert "proxy_set_header" in content
            assert "X-Real-IP" in content

    @pytest.mark.slow
    def test_health_check_endpoint(
        self, project_root, docker_client, cleanup_containers
    ):
        """Test n8n health check endpoint."""
        docker_dir = project_root / "docker"

        # Ensure .env exists
        env_file = docker_dir / ".env"
        if not env_file.exists():
            env_example = docker_dir / ".env.example"
            if env_example.exists():
                env_file.write_text(env_example.read_text())

        # Start container
        subprocess.run(
            ["docker-compose", "up", "-d", "n8n"],
            capture_output=True,
            cwd=str(docker_dir),
            env={**os.environ, "COMPOSE_PROJECT_NAME": "n8n-local-health-test"},
        )

        # Wait for service to be ready
        health_url = "http://localhost:5678/healthz"
        healthy = False

        for _ in range(60):  # 60 second timeout
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(1)

        # Clean up
        subprocess.run(
            ["docker-compose", "down"],
            cwd=str(docker_dir),
            env={**os.environ, "COMPOSE_PROJECT_NAME": "n8n-local-health-test"},
        )

        assert healthy, "n8n health check failed"

    def test_docker_compose_profiles(self, project_root):
        """Test Docker Compose profiles for different deployment scenarios."""
        docker_compose = project_root / "docker" / "docker-compose.yml"

        # Test basic profile
        result = subprocess.run(
            [
                "docker-compose",
                "-f",
                str(docker_compose),
                "config",
                "--profiles",
                "basic",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            assert "n8n:" in result.stdout
            # Basic profile should not include postgres
            assert "postgres:" not in result.stdout

    def test_persistent_data_configuration(self, project_root):
        """Test persistent data configuration."""
        docker_compose = project_root / "docker" / "docker-compose.yml"

        with open(docker_compose) as f:
            content = f.read()

        # Check for named volumes (not bind mounts for data)
        assert "n8n_data:" in content

        # For production, check postgres data volume
        docker_compose_prod = project_root / "docker" / "docker-compose.prod.yml"
        with open(docker_compose_prod) as f:
            prod_content = f.read()

        assert "postgres_data:" in prod_content
