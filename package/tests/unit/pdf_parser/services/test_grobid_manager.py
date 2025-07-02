"""Tests for GROBID service manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import docker
from requests.exceptions import ConnectionError, Timeout

from src.pdf_parser.services.grobid_manager import GROBIDManager, GROBIDServiceError


class TestGROBIDManager:
    """Test GROBID service manager."""
    
    def test_init_default_config(self):
        """Test initialization with default configuration."""
        manager = GROBIDManager()
        
        assert manager.grobid_url == 'http://localhost:8070'
        assert manager.container_name == 'grobid'
        assert manager.image_name == 'lfoppiano/grobid:0.7.3'
        assert manager.port == 8070
        assert manager.timeout == 30
    
    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            'url': 'http://custom:9000',
            'container_name': 'custom-grobid',
            'image': 'custom/grobid:1.0',
            'port': 9000,
            'timeout': 60
        }
        
        manager = GROBIDManager(config)
        
        assert manager.grobid_url == 'http://custom:9000'
        assert manager.container_name == 'custom-grobid'
        assert manager.image_name == 'custom/grobid:1.0'
        assert manager.port == 9000
        assert manager.timeout == 60
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_check_docker_connection_success(self, mock_docker):
        """Test successful Docker connection check."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        mock_client.ping.return_value = True
        
        manager = GROBIDManager()
        result = manager._check_docker_connection()
        
        assert result is True
        mock_client.ping.assert_called_once()
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_check_docker_connection_failure(self, mock_docker):
        """Test Docker connection failure."""
        mock_docker.side_effect = docker.errors.DockerException("Docker not available")
        
        manager = GROBIDManager()
        result = manager._check_docker_connection()
        
        assert result is False
    
    @patch('requests.get')
    def test_check_service_health_success(self, mock_get):
        """Test successful GROBID service health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "GROBID is alive"
        mock_get.return_value = mock_response
        
        manager = GROBIDManager()
        result = manager.check_service_health()
        
        assert result is True
        mock_get.assert_called_once_with(
            'http://localhost:8070/api/isalive',
            timeout=30
        )
    
    @patch('requests.get')
    def test_check_service_health_failure(self, mock_get):
        """Test GROBID service health check failure."""
        mock_get.side_effect = ConnectionError("Service not available")
        
        manager = GROBIDManager()
        result = manager.check_service_health()
        
        assert result is False
    
    @patch('requests.get')
    def test_check_service_health_timeout(self, mock_get):
        """Test GROBID service health check timeout."""
        mock_get.side_effect = Timeout("Request timed out")
        
        manager = GROBIDManager()
        result = manager.check_service_health()
        
        assert result is False
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_start_service_container_exists_running(self, mock_docker):
        """Test starting service when container exists and is running."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        mock_container = Mock()
        mock_container.status = 'running'
        mock_client.containers.get.return_value = mock_container
        
        manager = GROBIDManager()
        with patch.object(manager, 'check_service_health', return_value=True):
            result = manager.start_service()
        
        assert result is True
        mock_client.containers.get.assert_called_once_with('grobid')
        mock_container.start.assert_not_called()
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_start_service_container_exists_stopped(self, mock_docker):
        """Test starting service when container exists but is stopped."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        mock_container = Mock()
        mock_container.status = 'exited'
        mock_client.containers.get.return_value = mock_container
        
        manager = GROBIDManager()
        with patch.object(manager, 'check_service_health', return_value=True):
            result = manager.start_service()
        
        assert result is True
        mock_container.start.assert_called_once()
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_start_service_create_new_container(self, mock_docker):
        """Test starting service by creating new container."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        # Container doesn't exist
        mock_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        
        mock_container = Mock()
        mock_client.containers.run.return_value = mock_container
        
        manager = GROBIDManager()
        with patch.object(manager, 'check_service_health', return_value=True):
            result = manager.start_service()
        
        assert result is True
        mock_client.containers.run.assert_called_once_with(
            'lfoppiano/grobid:0.7.3',
            name='grobid',
            ports={'8070/tcp': 8070},
            detach=True,
            remove=False
        )
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_start_service_docker_error(self, mock_docker):
        """Test starting service with Docker error."""
        mock_docker.side_effect = docker.errors.DockerException("Docker error")
        
        manager = GROBIDManager()
        
        with pytest.raises(GROBIDServiceError, match="Docker is not available"):
            manager.start_service()
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_stop_service_success(self, mock_docker):
        """Test successful service stop."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container
        
        manager = GROBIDManager()
        result = manager.stop_service()
        
        assert result is True
        mock_container.stop.assert_called_once()
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_stop_service_container_not_found(self, mock_docker):
        """Test stopping service when container doesn't exist."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        mock_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        
        manager = GROBIDManager()
        result = manager.stop_service()
        
        assert result is True  # Consider it successful if container doesn't exist
    
    @patch('src.pdf_parser.services.grobid_manager.docker.from_env')
    def test_restart_service_success(self, mock_docker):
        """Test successful service restart."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container
        
        manager = GROBIDManager()
        with patch.object(manager, 'check_service_health', return_value=True):
            result = manager.restart_service()
        
        assert result is True
        mock_container.restart.assert_called_once()
    
    def test_get_service_status_healthy(self):
        """Test getting service status when healthy."""
        manager = GROBIDManager()
        
        with patch.object(manager, 'check_service_health', return_value=True):
            status = manager.get_service_status()
        
        expected = {
            'healthy': True,
            'url': 'http://localhost:8070',
            'container_name': 'grobid',
            'image': 'lfoppiano/grobid:0.7.3'
        }
        
        assert status == expected
    
    def test_get_service_status_unhealthy(self):
        """Test getting service status when unhealthy."""
        manager = GROBIDManager()
        
        with patch.object(manager, 'check_service_health', return_value=False):
            status = manager.get_service_status()
        
        expected = {
            'healthy': False,
            'url': 'http://localhost:8070',
            'container_name': 'grobid',
            'image': 'lfoppiano/grobid:0.7.3'
        }
        
        assert status == expected
    
    def test_ensure_service_running_already_healthy(self):
        """Test ensuring service is running when already healthy."""
        manager = GROBIDManager()
        
        with patch.object(manager, 'check_service_health', return_value=True):
            result = manager.ensure_service_running()
        
        assert result is True
    
    def test_ensure_service_running_needs_start(self):
        """Test ensuring service is running when it needs to be started."""
        manager = GROBIDManager()
        
        health_checks = [False, True]  # First unhealthy, then healthy after start
        
        with patch.object(manager, 'check_service_health', side_effect=health_checks):
            with patch.object(manager, 'start_service', return_value=True):
                result = manager.ensure_service_running()
        
        assert result is True
    
    def test_ensure_service_running_start_fails(self):
        """Test ensuring service is running when start fails."""
        manager = GROBIDManager()
        
        with patch.object(manager, 'check_service_health', return_value=False):
            with patch.object(manager, 'start_service', side_effect=GROBIDServiceError("Start failed")):
                with pytest.raises(GROBIDServiceError):
                    manager.ensure_service_running()