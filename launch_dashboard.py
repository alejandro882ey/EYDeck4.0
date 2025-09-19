import os
import sys
import webbrowser
import subprocess
import socket
import shutil
import glob
from subprocess import Popen
from pathlib import Path

def get_script_directory():
    """Get the absolute path of the directory containing this script."""
    return Path(os.path.dirname(os.path.abspath(__file__)))

def get_local_venv_directory():
    """Get a local directory for virtual environment to avoid network drive issues."""
    # Use local AppData to avoid permission issues with network drives
    local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
    return Path(local_appdata) / "EYDashboard" / "venv"

def is_network_drive():
    """Check if we're running from a network drive."""
    script_dir = get_script_directory()
    drive_letter = str(script_dir).split(':')[0].upper()
    # Network drives are typically mapped to letters X, Y, Z or UNC paths
    return drive_letter in ['X', 'Y', 'Z'] or str(script_dir).startswith('\\\\')

def is_local_machine():
    """Check if this is your development machine by hostname."""
    return socket.gethostname() == "XW43XYRW3"  # Your actual hostname

def find_python_executable():
    """Find the best available Python executable."""
    print("🔍 Searching for Python installations...")
    
    # Try current Python first (if script is running)
    if sys.executable and os.path.exists(sys.executable):
        print(f"✅ Using current Python: {sys.executable}")
        return sys.executable
    
    # Try common Python commands
    for cmd in ['python', 'python3', 'py']:
        try:
            result = subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and 'Python' in result.stdout:
                python_path = shutil.which(cmd)
                if python_path:
                    print(f"✅ Found Python via '{cmd}': {python_path}")
                    return python_path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    # Search common installation directories
    search_patterns = [
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python*', 'python.exe'),
        r"C:\Python*\python.exe",
        r"C:\Program Files\Python*\python.exe",
        r"C:\Program Files (x86)\Python*\python.exe"
    ]
    
    for pattern in search_patterns:
        try:
            matches = glob.glob(pattern)
            for match in matches:
                if os.path.exists(match):
                    try:
                        result = subprocess.run([match, '--version'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0 and 'Python' in result.stdout:
                            print(f"✅ Found Python at: {match}")
                            return match
                    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                        continue
        except Exception:
            continue
    
    print("❌ No Python installation found")
    return None

def create_virtual_environment():
    """Create virtual environment in local directory."""
    python_exe = find_python_executable()
    if not python_exe:
        raise RuntimeError("Cannot create virtual environment: Python not found")
    
    venv_path = get_local_venv_directory()
    
    if venv_path.exists() and (venv_path / "Scripts" / "python.exe").exists():
        print(f"✅ Virtual environment already exists at {venv_path}")
        return str(venv_path / "Scripts" / "python.exe")
    
    print(f"🔧 Creating virtual environment at {venv_path}...")
    
    # Ensure parent directory exists
    venv_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Try using venv module
        subprocess.check_call([python_exe, "-m", "venv", str(venv_path)])
        print("✅ Virtual environment created successfully")
        
        venv_python = venv_path / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        else:
            raise FileNotFoundError("Virtual environment Python not found after creation")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating virtual environment: {e}")
        print(f"🚫 Will use system Python instead")
        return python_exe

def get_python_path():
    """Get the appropriate Python path based on environment."""
    if is_local_machine():
        # Use system Python on local machine
        python_exe = find_python_executable()
        if not python_exe:
            raise RuntimeError("Python not found on local machine")
        return python_exe
    else:
        # Use virtual environment Python on other machines
        # Create in local directory to avoid network drive issues
        return create_virtual_environment()

def install_requirements():
    """Install requirements from requirements.txt."""
    base_dir = get_script_directory()
    python_path = get_python_path()
    requirements_path = base_dir / "requirements.txt"
    
    if not requirements_path.exists():
        print("⚠️  requirements.txt not found, skipping package installation")
        return
    
    print(f"📦 Installing requirements from {requirements_path}...")
    try:
        # Upgrade pip first
        print("📤 Upgrading pip...")
        subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        
        # Install requirements
        print("📦 Installing packages...")
        subprocess.check_call([python_path, "-m", "pip", "install", "-r", str(requirements_path)], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print("✅ Requirements installed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Error installing requirements: {e}")
        print("🌐 Please ensure you have internet connection")
        print("⚠️  Continuing without package updates (some features may not work)")

def launch_dashboard():
    """Main launch process."""
    print("🎯 EY Dashboard Launcher")
    print("=" * 50)
    
    # Check if running from network drive
    if is_network_drive():
        print("🌐 Network drive detected - using local virtual environment")
    
    try:
        base_dir = get_script_directory()
        
        # Determine Python path and setup
        if is_local_machine():
            print("🏠 Development machine - using system Python")
            python_path = get_python_path()
        else:
            print("🌍 New machine - setting up isolated environment")
            python_path = get_python_path()
            install_requirements()
        
        print(f"🐍 Using Python: {python_path}")
        print("🚀 Starting EY Dashboard...")
        
        # Verify manage.py exists
        manage_py_path = base_dir / "manage.py"
        if not manage_py_path.exists():
            raise FileNotFoundError(f"manage.py not found at {manage_py_path}")
        
        # Change to script directory (important for Django)
        os.chdir(base_dir)
        
        # Start Django development server on port 8001 (as required)
        print("🌐 Starting Django server on port 8001...")
        server_process = Popen([python_path, str(manage_py_path), "runserver", "8001"])
        
        # Wait a moment for the server to start
        import time
        time.sleep(3)
        
        # Open the browser
        dashboard_url = 'http://127.0.0.1:8001'
        print(f"🌐 Opening dashboard at: {dashboard_url}")
        webbrowser.open(dashboard_url)
        
        print("=" * 50)
        print("✅ EY Dashboard is running!")
        print("📱 Browser should open automatically")
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        try:
            server_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping the server...")
            server_process.terminate()
            server_process.wait()
            print("✅ Server stopped successfully.")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\n🔧 Troubleshooting tips:")
        print("   • Ensure Python is properly installed")
        print("   • Check if you have internet connection") 
        print("   • Verify port 8001 is available")
        print("   • Try running as administrator")
        print("   • Check Windows Defender/Antivirus settings")
        sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Please ensure you're in the correct directory and Python is properly installed.")
        sys.exit(1)

if __name__ == "__main__":
    launch_dashboard()
