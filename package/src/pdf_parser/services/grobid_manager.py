"""GROBID service management with Docker integration."""

import logging
import time
from typing import Dict, Any, Optional

import docker
import requests
from requests.exceptions import ConnectionError, Timeout

logger = logging.getLogger(__name__)


class GROBIDServiceError(Exception):
    """Exception raised for GROBID service management errors."""
    pass


class GROBIDManager:
    """Manages GROBID service lifecycle using Docker."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize GROBID manager.
        
        Args:
            config: Configuration dictionary with optional keys:
                - url: GROBID service URL (default: http://localhost:8070)
                - container_name: Docker container name (default: grobid)
                - image: Docker image (default: lfoppiano/grobid:0.7.3)
                - port: Port to expose (default: 8070)
                - timeout: Request timeout (default: 30)
        """
        config = config or {}
        
        self.grobid_url = config.get('url', 'http://localhost:8070')
        self.container_name = config.get('container_name', 'grobid')
        self.image_name = config.get('image', 'lfoppiano/grobid:0.7.3')
        self.port = config.get('port', 8070)
        self.timeout = config.get('timeout', 30)
        
        logger.info(f"Initialized GROBID manager for {self.grobid_url}")
    
    def _check_docker_connection(self) -> bool:
        """Check if Docker is available and accessible.
        
        Returns:
            True if Docker is available, False otherwise
        """
        try:
            client = docker.from_env()
            client.ping()
            return True
        except (docker.errors.DockerException, Exception) as e:
            logger.error(f"Docker connection failed: {str(e)}")
            return False
    
    def check_service_health(self) -> bool:
        """Check if GROBID service is healthy and responding.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = requests.get(
                f'{self.grobid_url}/api/isalive',
                timeout=self.timeout
            )
            
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.debug("GROBID service is healthy")
            else:
                logger.warning(f"GROBID service unhealthy: {response.status_code}")
            
            return is_healthy
            
        except (ConnectionError, Timeout) as e:
            logger.warning(f"GROBID service health check failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during health check: {str(e)}")
            return False
    
    def start_service(self) -> bool:
        """Start GROBID service using Docker.
        
        Returns:
            True if service started successfully
            
        Raises:
            GROBIDServiceError: If service fails to start
        """
        if not self._check_docker_connection():
            raise GROBIDServiceError("Docker is not available")
        
        try:
            client = docker.from_env()
            
            # Check if container already exists
            try:
                container = client.containers.get(self.container_name)
                
                if container.status == 'running':
                    logger.info(f"GROBID container '{self.container_name}' already running")
                    
                    # Verify service is actually healthy
                    if self.check_service_health():
                        return True
                    else:
                        logger.warning("Container running but service unhealthy, restarting...")
                        container.restart()
                else:
                    logger.info(f"Starting existing GROBID container '{self.container_name}'")
                    container.start()
                    
            except docker.errors.NotFound:
                # Container doesn't exist, create new one
                logger.info(f"Creating new GROBID container '{self.container_name}'")
                container = client.containers.run(
                    self.image_name,
                    name=self.container_name,
                    ports={'8070/tcp': self.port},
                    detach=True,
                    remove=False
                )
            
            # Wait for service to become healthy
            max_wait = 60  # seconds
            wait_interval = 2  # seconds
            waited = 0
            
            while waited < max_wait:
                if self.check_service_health():
                    logger.info(f"GROBID service started successfully after {waited}s")
                    return True
                
                time.sleep(wait_interval)
                waited += wait_interval
            
            raise GROBIDServiceError(f"GROBID service failed to become healthy within {max_wait}s")
            
        except docker.errors.DockerException as e:
            raise GROBIDServiceError(f"Failed to start GROBID service: {str(e)}")
        except Exception as e:
            raise GROBIDServiceError(f"Unexpected error starting GROBID service: {str(e)}")
    
    def stop_service(self) -> bool:
        """Stop GROBID service.
        
        Returns:
            True if service stopped successfully
        """
        try:
            client = docker.from_env()
            container = client.containers.get(self.container_name)
            container.stop()
            logger.info(f"GROBID container '{self.container_name}' stopped")
            return True
            
        except docker.errors.NotFound:
            logger.info(f"GROBID container '{self.container_name}' not found (already stopped)")
            return True
        except docker.errors.DockerException as e:
            logger.error(f"Failed to stop GROBID service: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error stopping GROBID service: {str(e)}")
            return False
    
    def restart_service(self) -> bool:
        """Restart GROBID service.
        
        Returns:
            True if service restarted successfully
            
        Raises:
            GROBIDServiceError: If service fails to restart
        """
        try:
            client = docker.from_env()
            container = client.containers.get(self.container_name)
            container.restart()
            
            # Wait for service to become healthy
            max_wait = 60
            wait_interval = 2
            waited = 0
            
            while waited < max_wait:
                if self.check_service_health():
                    logger.info(f"GROBID service restarted successfully after {waited}s")
                    return True
                
                time.sleep(wait_interval)
                waited += wait_interval
            
            raise GROBIDServiceError(f"GROBID service failed to become healthy after restart")
            
        except docker.errors.NotFound:
            # Container doesn't exist, start it
            return self.start_service()
        except docker.errors.DockerException as e:
            raise GROBIDServiceError(f"Failed to restart GROBID service: {str(e)}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status.
        
        Returns:
            Dictionary with service status information
        """
        return {
            'healthy': self.check_service_health(),
            'url': self.grobid_url,
            'container_name': self.container_name,
            'image': self.image_name
        }
    
    def ensure_service_running(self) -> bool:
        """Ensure GROBID service is running and healthy.
        
        Returns:
            True if service is running and healthy
            
        Raises:
            GROBIDServiceError: If service cannot be started
        """
        if self.check_service_health():
            logger.debug("GROBID service already running and healthy")
            return True
        
        logger.info("GROBID service not healthy, attempting to start...")
        return self.start_service()