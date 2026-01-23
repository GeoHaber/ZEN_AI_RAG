"""
Setup Manager - Automated Environment Setup and Validation
Handles CPU detection, binary downloads, and dependency checks.
Designed to be bundled into executables (PyInstaller, etc.)
"""

import os
import sys
import platform
import subprocess
import requests
import zipfile
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import tempfile


class HardwareDetector:
    """Detect CPU capabilities and optimal binary configuration."""

    @staticmethod
    def detect_cpu_features() -> Dict[str, bool]:
        """Detect CPU instruction set features (AVX, AVX2, AVX512, etc.)

        Important for AMD Ryzen AI and modern CPUs with AI acceleration.
        """
        features = {
            'avx': False,
            'avx2': False,
            'avx512': False,
            'fma': False,
            'sse4_1': False,
            'sse4_2': False,
        }

        # Try py-cpuinfo (works on all platforms)
        try:
            import cpuinfo
            info = cpuinfo.get_cpu_info()
            flags = info.get('flags', [])

            # Convert to lowercase for case-insensitive matching
            flags_lower = [str(f).lower() for f in flags]

            features['avx'] = 'avx' in flags_lower
            features['avx2'] = 'avx2' in flags_lower
            # AVX-512 has many variants (f, bw, cd, dq, vl, etc.)
            features['avx512'] = any('avx512' in f for f in flags_lower)
            # FMA can be fma, fma3, or fma4
            features['fma'] = any(f in flags_lower for f in ['fma', 'fma3', 'fma4'])
            features['sse4_1'] = 'sse4_1' in flags_lower or 'sse4.1' in flags_lower
            features['sse4_2'] = 'sse4_2' in flags_lower or 'sse4.2' in flags_lower

            return features
        except ImportError:
            # py-cpuinfo not available, try to install it
            print("[Setup] Installing py-cpuinfo for CPU detection...")
            try:
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install', 'py-cpuinfo', '--quiet'],
                    timeout=60
                )
                # Try again after installation
                import cpuinfo
                info = cpuinfo.get_cpu_info()
                flags = info.get('flags', [])
                flags_lower = [str(f).lower() for f in flags]

                features['avx'] = 'avx' in flags_lower
                features['avx2'] = 'avx2' in flags_lower
                features['avx512'] = any('avx512' in f for f in flags_lower)
                features['fma'] = any(f in flags_lower for f in ['fma', 'fma3', 'fma4'])
                features['sse4_1'] = 'sse4_1' in flags_lower or 'sse4.1' in flags_lower
                features['sse4_2'] = 'sse4_2' in flags_lower or 'sse4.2' in flags_lower

                return features
            except Exception:
                pass

        # Fallback for Windows - check CPU name
        if sys.platform == 'win32':
            try:
                cmd = 'powershell -NoProfile -Command "Get-WmiObject Win32_Processor | Select-Object Name"'
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=5
                )
                cpu_name = result.stdout.lower()

                # AMD Ryzen and Intel Core (modern) CPUs have these features
                if 'ryzen' in cpu_name or 'core i' in cpu_name or 'xeon' in cpu_name:
                    features['avx'] = True
                    features['avx2'] = True
                    features['fma'] = True
                    features['sse4_1'] = True
                    features['sse4_2'] = True

                    # Ryzen AI and newer Intel have AVX-512
                    if 'ryzen ai' in cpu_name or '12th gen' in cpu_name or '13th gen' in cpu_name or '14th gen' in cpu_name:
                        features['avx512'] = True

            except Exception:
                pass

        elif sys.platform == 'linux':
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read().lower()
                    features['avx'] = 'avx' in cpuinfo
                    features['avx2'] = 'avx2' in cpuinfo
                    features['avx512'] = 'avx512' in cpuinfo
                    features['fma'] = 'fma' in cpuinfo
                    features['sse4_1'] = 'sse4_1' in cpuinfo
                    features['sse4_2'] = 'sse4_2' in cpuinfo
            except Exception:
                pass

        elif sys.platform == 'darwin':
            try:
                result = subprocess.run(
                    ['sysctl', '-a'], capture_output=True, text=True, timeout=5
                )
                sysctl_out = result.stdout.lower()
                features['avx'] = 'avx1.0' in sysctl_out
                features['avx2'] = 'avx2.0' in sysctl_out
            except Exception:
                pass

        return features

    @staticmethod
    def detect_gpu() -> Dict[str, any]:
        """Detect GPU availability (NVIDIA CUDA, AMD Radeon/ROCm)"""
        gpu_info = {
            'has_nvidia': False,
            'cuda_version': None,
            'has_amd': False,
            'gpu_name': None,
        }

        if sys.platform == 'win32':
            # Check for NVIDIA GPU first
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    gpu_info['has_nvidia'] = True
                    gpu_info['gpu_name'] = result.stdout.strip().split(',')[0]

                    # Try to get CUDA version
                    cuda_result = subprocess.run(
                        ['nvidia-smi'], capture_output=True, text=True, timeout=5
                    )
                    if 'CUDA Version' in cuda_result.stdout:
                        for line in cuda_result.stdout.split('\n'):
                            if 'CUDA Version' in line:
                                parts = line.split('CUDA Version:')
                                if len(parts) > 1:
                                    gpu_info['cuda_version'] = parts[1].strip().split()[0]
                    return gpu_info  # Found NVIDIA, no need to check AMD
            except Exception:
                pass

            # Check for AMD GPU (integrated or discrete)
            try:
                cmd = 'powershell -NoProfile -Command "Get-WmiObject Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json"'
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    import json
                    gpus = json.loads(result.stdout)
                    if not isinstance(gpus, list):
                        gpus = [gpus]

                    for gpu in gpus:
                        name = gpu.get('Name', '').upper()
                        if 'AMD' in name or 'RADEON' in name:
                            gpu_info['has_amd'] = True
                            gpu_info['gpu_name'] = gpu.get('Name', 'AMD GPU')
                            break
            except Exception:
                pass

        return gpu_info

    @staticmethod
    def get_optimal_binary_type() -> str:
        """Determine the best llama.cpp binary variant to download."""
        gpu_info = HardwareDetector.detect_gpu()
        cpu_features = HardwareDetector.detect_cpu_features()

        # Priority 1: CUDA if available
        if gpu_info['has_nvidia'] and gpu_info['cuda_version']:
            try:
                cuda_major = int(gpu_info['cuda_version'].split('.')[0])
                if cuda_major >= 12:
                    return 'cuda-cu12'
                elif cuda_major >= 11:
                    return 'cuda-cu11'
            except Exception:
                pass

        # Priority 2: CPU with best instruction set
        if cpu_features['avx512']:
            return 'cpu-avx512'
        elif cpu_features['avx2']:
            return 'cpu-avx2'
        elif cpu_features['avx']:
            return 'cpu-avx'

        # Fallback: Basic CPU
        return 'cpu'


class BinaryDownloader:
    """Download and install llama.cpp binaries from GitHub."""

    GITHUB_API = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"

    def __init__(self, install_dir: Path):
        self.install_dir = Path(install_dir)
        self.install_dir.mkdir(parents=True, exist_ok=True)

    def get_latest_release(self) -> Dict:
        """Fetch latest llama.cpp release information."""
        print("[Setup] Fetching latest llama.cpp release...")
        try:
            response = requests.get(self.GITHUB_API, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to fetch release info: {e}")

    def find_best_asset(self, release_data: Dict, binary_type: str) -> Optional[Dict]:
        """Find the best matching binary asset for the system."""
        assets = release_data.get('assets', [])

        if sys.platform == 'win32':
            platform_key = 'win'
            arch = 'x64' if platform.machine().endswith('64') else 'x86'
        elif sys.platform == 'linux':
            platform_key = 'linux'
            arch = 'x64'
        elif sys.platform == 'darwin':
            platform_key = 'macos'
            arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
        else:
            return None

        # Build search patterns in priority order
        patterns = []

        if 'cuda' in binary_type:
            patterns.append(f"llama-.*{binary_type}.*{platform_key}.*{arch}.*\\.zip")
        else:
            # For CPU builds, look for specific variant first
            if 'avx512' in binary_type:
                patterns.append(f"llama-.*bin-{platform_key}-avx512.*{arch}.*\\.zip")
            elif 'avx2' in binary_type:
                patterns.append(f"llama-.*bin-{platform_key}-avx2.*{arch}.*\\.zip")
            elif 'avx' in binary_type:
                patterns.append(f"llama-.*bin-{platform_key}-avx.*{arch}.*\\.zip")

            # Generic CPU build fallback (but exclude CUDA builds)
            patterns.append(f"llama-.*bin-{platform_key}(?!.*cuda).*{arch}.*\\.zip")

        import re
        for pattern in patterns:
            for asset in assets:
                if re.search(pattern, asset['name'], re.IGNORECASE):
                    return asset

        return None

    def download_and_extract(self, asset: Dict) -> bool:
        """Download and extract the binary package."""
        url = asset['browser_download_url']
        filename = asset['name']
        temp_path = None

        print(f"[Setup] Downloading {filename}...")
        print(f"[Setup] Size: {asset.get('size', 0) // (1024*1024)} MB")

        try:
            # Download with progress
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                temp_path = tmp_file.name
                try:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # Filter out keep-alive chunks
                            tmp_file.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\r[Setup] Progress: {percent:.1f}%", end='', flush=True)
                except Exception as download_error:
                    print(f"\n[Setup] Download interrupted: {download_error}")
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                    return False

            print("\n[Setup] Extracting binaries...")

            try:
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    # Extract all files
                    zip_ref.extractall(self.install_dir)
                    extracted_files = zip_ref.namelist()
                    print(f"[Setup] Extracted {len(extracted_files)} files")
            except zipfile.BadZipFile:
                print("[Setup] Error: Downloaded file is corrupted or incomplete")
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
            except Exception as extract_error:
                print(f"[Setup] Extraction error: {extract_error}")
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                return False

            # Cleanup temp file
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass  # Ignore cleanup errors

            # Verify critical binaries exist
            try:
                if sys.platform == 'win32':
                    server_exe = self.install_dir / 'llama-server.exe'
                else:
                    server_exe = self.install_dir / 'llama-server'

                if not server_exe.exists():
                    # Sometimes files are in a subdirectory
                    for file in self.install_dir.rglob('llama-server*'):
                        if file.is_file():
                            print(f"[Setup] Found server at: {file}")
                            return True

                    raise Exception("llama-server not found in extracted files")

                print(f"[Setup] [OK] Binary installed: {server_exe.name}")
                return True
            except Exception as verify_error:
                print(f"[Setup] Verification error: {verify_error}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"\n[Setup] Network error: {e}")
            print("[Setup] Please check your internet connection and try again")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False
        except Exception as e:
            print(f"\n[Setup] Unexpected error: {e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False

    def install(self) -> bool:
        """Main installation method."""
        # Check if already installed
        if sys.platform == 'win32':
            server_exe = self.install_dir / 'llama-server.exe'
        else:
            server_exe = self.install_dir / 'llama-server'

        if server_exe.exists():
            print(f"[Setup] Binary already exists: {server_exe}")
            return True

        # Detect optimal binary type
        binary_type = HardwareDetector.get_optimal_binary_type()
        print(f"[Setup] Detected optimal build: {binary_type}")

        # Get latest release
        release_data = self.get_latest_release()
        print(f"[Setup] Latest version: {release_data.get('tag_name', 'unknown')}")

        # Find best asset
        asset = self.find_best_asset(release_data, binary_type)
        if not asset:
            print(f"[Setup] Could not find suitable binary for {binary_type}")
            print(f"[Setup] Please download manually from: {release_data.get('html_url')}")
            return False

        # Download and extract
        return self.download_and_extract(asset)


class DependencyChecker:
    """Check and install Python dependencies."""

    REQUIRED_PACKAGES = [
        'nicegui',
        'httpx',
        'faiss-cpu',
        'sentence-transformers',
        'numpy',
        'PyPDF2',
    ]

    OPTIONAL_PACKAGES = [
        'torch',
        'pyttsx3',
        'sounddevice',
        'scipy',
    ]

    # CPU info is actually required for proper hardware detection
    SYSTEM_PACKAGES = [
        'py-cpuinfo',  # Required for CPU feature detection
    ]

    @staticmethod
    def check_package(package_name: str) -> bool:
        """Check if a package is installed."""
        try:
            __import__(package_name.replace('-', '_'))
            return True
        except ImportError:
            return False

    @staticmethod
    def install_package(package_name: str) -> bool:
        """Install a package using pip."""
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', package_name, '--quiet'],
                timeout=300
            )
            return True
        except Exception as e:
            print(f"[Setup] Failed to install {package_name}: {e}")
            return False

    @staticmethod
    def check_and_install_dependencies(auto_install: bool = False) -> Tuple[List[str], List[str]]:
        """Check all dependencies and optionally install missing ones."""
        missing = []
        installed = []

        print("[Setup] Checking Python dependencies...")

        # First ensure system packages (like cpuinfo) are installed
        for package in DependencyChecker.SYSTEM_PACKAGES:
            if not DependencyChecker.check_package(package):
                print(f"[Setup] Installing system package: {package}...")
                if DependencyChecker.install_package(package):
                    installed.append(package)

        # Then check required packages
        for package in DependencyChecker.REQUIRED_PACKAGES:
            display_name = package.replace('_', '-')
            if DependencyChecker.check_package(package):
                print(f"  [OK] {display_name}")
            else:
                print(f"  [MISS] {display_name}")
                missing.append(package)

                if auto_install:
                    print(f"[Setup] Installing {display_name}...")
                    if DependencyChecker.install_package(package):
                        installed.append(package)
                        missing.remove(package)

        return missing, installed


class SetupManager:
    """Main setup orchestrator."""

    def __init__(self, base_dir: Path = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.bin_dir = self.base_dir / '_bin'
        self.config_path = self.base_dir / 'config.json'

    def detect_hardware(self) -> Dict:
        """Detect and display hardware information."""
        print("\n" + "="*60)
        print("HARDWARE DETECTION")
        print("="*60)

        cpu_features = HardwareDetector.detect_cpu_features()
        gpu_info = HardwareDetector.detect_gpu()

        print(f"Platform: {sys.platform}")
        print(f"Architecture: {platform.machine()}")
        print(f"CPU Features:")
        for feature, available in cpu_features.items():
            status = "[OK]" if available else "[NO]"
            print(f"  {status} {feature.upper()}")

        if gpu_info['has_nvidia']:
            print(f"\nGPU: {gpu_info['gpu_name']}")
            print(f"CUDA Version: {gpu_info['cuda_version']}")
        elif gpu_info['has_amd']:
            print(f"\nGPU: {gpu_info['gpu_name']} (AMD)")
            print("Note: AMD ROCm support available for Linux")
        else:
            print("\nGPU: No dedicated GPU detected (CPU mode)")

        optimal = HardwareDetector.get_optimal_binary_type()
        print(f"\nRecommended Build: {optimal}")
        print("="*60 + "\n")

        return {
            'cpu_features': cpu_features,
            'gpu_info': gpu_info,
            'optimal_build': optimal,
        }

    def setup_binaries(self, force: bool = False) -> bool:
        """Download and install llama.cpp binaries."""
        print("\n" + "="*60)
        print("BINARY SETUP")
        print("="*60)

        downloader = BinaryDownloader(self.bin_dir)

        if not force:
            # Check if already installed
            if sys.platform == 'win32':
                server_exe = self.bin_dir / 'llama-server.exe'
            else:
                server_exe = self.bin_dir / 'llama-server'

            if server_exe.exists():
                size_mb = server_exe.stat().st_size // (1024*1024)
                print(f"[Setup] Binary already installed: {server_exe.name} ({size_mb} MB)")
                print("[Setup] Use --force to reinstall")
                return True

        success = downloader.install()
        print("="*60 + "\n")
        return success

    def check_dependencies(self, auto_install: bool = False) -> bool:
        """Check and optionally install Python dependencies."""
        print("\n" + "="*60)
        print("DEPENDENCY CHECK")
        print("="*60)

        missing, installed = DependencyChecker.check_and_install_dependencies(auto_install)

        if missing:
            print(f"\n[Setup] Missing packages: {', '.join(missing)}")
            print(f"[Setup] Install with: pip install {' '.join(missing)}")
            print("="*60 + "\n")
            return False

        if installed:
            print(f"\n[Setup] Installed: {', '.join(installed)}")

        print("\n[Setup] [OK] All required dependencies available!")
        print("="*60 + "\n")
        return True

    def verify_config(self) -> bool:
        """Verify config.json has correct paths."""
        if not self.config_path.exists():
            print(f"[Setup] Warning: config.json not found at {self.config_path}")
            return False

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Update bin_dir if needed
            expected_bin_dir = str(self.bin_dir).replace('\\', '\\\\')
            current_bin_dir = config.get('bin_dir', '')

            if current_bin_dir != expected_bin_dir:
                print(f"[Setup] Updating config.json bin_dir to: {self.bin_dir}")
                config['bin_dir'] = expected_bin_dir

                with open(self.config_path, 'w') as f:
                    json.dump(config, f, indent=4)

            return True

        except Exception as e:
            print(f"[Setup] Error updating config: {e}")
            return False

    def run_full_setup(self, auto_install: bool = False, force_binaries: bool = False) -> bool:
        """Run complete setup process."""
        print("\n" + "="*70)
        print(" " * 15 + "ZENA AI - SETUP MANAGER")
        print("="*70)

        # Step 1: Hardware detection
        hw_info = self.detect_hardware()

        # Step 2: Binary setup
        if not self.setup_binaries(force=force_binaries):
            print("\n[Setup] ✗ Binary setup failed!")
            return False

        # Step 3: Dependency check
        if not self.check_dependencies(auto_install=auto_install):
            if not auto_install:
                print("\n[Setup] ✗ Dependencies missing! Run with --auto-install to fix.")
                return False

        # Step 4: Verify config
        self.verify_config()

        # Final summary
        print("\n" + "="*70)
        print("SETUP COMPLETE! [OK]")
        print("="*70)
        print("\nYou can now run:")
        print("  python start_llm.py")
        print("\nTo open the UI:")
        print("  http://localhost:8080")
        print("="*70 + "\n")

        return True


def main():
    """Main entry point for setup script."""
    import argparse

    parser = argparse.ArgumentParser(description='ZENA AI Setup Manager')
    parser.add_argument('--auto-install', action='store_true',
                        help='Automatically install missing dependencies')
    parser.add_argument('--force', action='store_true',
                        help='Force reinstall binaries even if they exist')
    parser.add_argument('--detect-only', action='store_true',
                        help='Only detect hardware, don\'t install anything')
    parser.add_argument('--binaries-only', action='store_true',
                        help='Only download binaries')
    parser.add_argument('--deps-only', action='store_true',
                        help='Only check/install dependencies')

    args = parser.parse_args()

    manager = SetupManager()

    if args.detect_only:
        manager.detect_hardware()
        return

    if args.binaries_only:
        success = manager.setup_binaries(force=args.force)
        sys.exit(0 if success else 1)

    if args.deps_only:
        success = manager.check_dependencies(auto_install=args.auto_install)
        sys.exit(0 if success else 1)

    # Full setup
    success = manager.run_full_setup(
        auto_install=args.auto_install,
        force_binaries=args.force
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
