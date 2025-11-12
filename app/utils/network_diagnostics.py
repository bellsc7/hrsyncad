import socket
import subprocess
import platform
import logging
from config import Config

logger = logging.getLogger(__name__)

def check_dns_resolution(hostname):
    """
    Check if DNS resolution works for the given hostname
    """
    try:
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"DNS resolution successful: {hostname} -> {ip_address}")
        return True, ip_address
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed for {hostname}: {e}")
        return False, str(e)

def check_port_connectivity(host, port, timeout=10):
    """
    Check if a specific port is open on the target host
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.info(f"Port {port} is open on {host}")
            return True
        else:
            logger.error(f"Port {port} is closed on {host} - Error code: {result}")
            return False
    except socket.error as e:
        logger.error(f"Error checking port {port} on {host}: {e}")
        return False

def ping_host(host, count=3):
    """
    Ping the host to check basic network connectivity
    """
    try:
        # Determine the correct ping command based on the platform
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, str(count), host]
        
        # Run the ping command
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"Ping to {host} successful")
            return True, result.stdout
        else:
            logger.error(f"Ping to {host} failed: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"Ping to {host} timed out")
        return False, "Ping timed out"
    except Exception as e:
        logger.error(f"Error pinging {host}: {e}")
        return False, str(e)

def run_ad_connectivity_diagnostics():
    """
    Run comprehensive diagnostics for AD server connectivity
    """
    logger.info("Starting AD connectivity diagnostics")
    
    ad_server = Config.AD_SERVER
    ad_port = getattr(Config, 'AD_PORT', 389)
    
    diagnostics = {
        'dns_resolution': False,
        'ping': False,
        'port_connectivity': False,
        'details': {}
    }
    
    # 1. Check DNS resolution
    dns_success, dns_result = check_dns_resolution(ad_server)
    diagnostics['dns_resolution'] = dns_success
    diagnostics['details']['dns'] = dns_result
    
    # 2. Ping the server
    ping_success, ping_result = ping_host(ad_server)
    diagnostics['ping'] = ping_success
    diagnostics['details']['ping'] = ping_result
    
    # 3. Check port connectivity
    port_success = check_port_connectivity(ad_server, ad_port)
    diagnostics['port_connectivity'] = port_success
    
    # 4. Summary
    all_tests_passed = dns_success and ping_success and port_success
    diagnostics['overall_status'] = 'PASS' if all_tests_passed else 'FAIL'
    
    logger.info(f"AD connectivity diagnostics completed: {diagnostics['overall_status']}")
    
    return diagnostics

def troubleshoot_ad_connection():
    """
    Provide troubleshooting recommendations based on diagnostic results
    """
    diagnostics = run_ad_connectivity_diagnostics()
    recommendations = []
    
    if not diagnostics['dns_resolution']:
        recommendations.append(
            "DNS resolution failed. Check:\n"
            "- Verify the AD server hostname is correct\n"
            "- Check DNS server configuration\n"
            "- Try using IP address directly in AD_SERVER config"
        )
    
    if not diagnostics['ping']:
        recommendations.append(
            "Ping failed. Check:\n"
            "- Network connectivity between application server and AD server\n"
            "- Firewall rules allowing ICMP traffic\n"
            "- AD server is powered on and connected to network"
        )
    
    if not diagnostics['port_connectivity']:
        recommendations.append(
            f"Port {getattr(Config, 'AD_PORT', 389)} is not accessible. Check:\n"
            "- LDAP service is running on AD server\n"
            "- Firewall rules allowing LDAP traffic (port 389 or 636 for LDAPS)\n"
            "- Network routing between application and AD server\n"
            "- AD server is not blocking connections from your application IP"
        )
    
    if diagnostics['overall_status'] == 'PASS':
        recommendations.append(
            "Basic connectivity tests passed. The issue might be:\n"
            "- Authentication credentials (username/password)\n"
            "- LDAP permissions for the configured user\n"
            "- SSL/TLS configuration if using LDAPS\n"
            "- Active Directory service-specific issues"
        )
    
    return {
        'diagnostics': diagnostics,
        'recommendations': recommendations
    }