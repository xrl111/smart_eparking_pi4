#!/usr/bin/env python3
"""Script để clean dự án - xóa cache, log, temp files."""

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def clean_pycache():
    """Xóa tất cả __pycache__ folders (trừ .venv)."""
    removed = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Bỏ qua .venv
        if '.venv' in root:
            continue
        
        if '__pycache__' in dirs:
            cache_dir = Path(root) / '__pycache__'
            shutil.rmtree(cache_dir, ignore_errors=True)
            removed.append(str(cache_dir.relative_to(PROJECT_ROOT)))
            dirs.remove('__pycache__')
    
    if removed:
        print(f"✅ Đã xóa {len(removed)} __pycache__ folders")
        for r in removed:
            print(f"   - {r}")
    else:
        print("✅ Không có __pycache__ folders để xóa")


def clean_pyc_files():
    """Xóa tất cả .pyc files (trừ .venv)."""
    removed = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Bỏ qua .venv
        if '.venv' in root:
            continue
        
        for file in files:
            if file.endswith(('.pyc', '.pyo', '.pyd')):
                file_path = Path(root) / file
                file_path.unlink(missing_ok=True)
                removed.append(str(file_path.relative_to(PROJECT_ROOT)))
    
    if removed:
        print(f"✅ Đã xóa {len(removed)} .pyc files")
    else:
        print("✅ Không có .pyc files để xóa")


def clean_logs():
    """Xóa log files."""
    log_files = [
        PROJECT_ROOT / 'parking.log',
        PROJECT_ROOT / '*.log',
    ]
    
    removed = []
    for pattern in log_files:
        if pattern.is_file():
            pattern.unlink()
            removed.append(pattern.name)
        else:
            # Tìm các file .log
            for log_file in PROJECT_ROOT.glob('*.log'):
                if log_file.is_file():
                    log_file.unlink()
                    removed.append(log_file.name)
    
    if removed:
        print(f"✅ Đã xóa {len(removed)} log files")
        for r in removed:
            print(f"   - {r}")
    else:
        print("✅ Không có log files để xóa")


def clean_temp_files():
    """Xóa temp files."""
    temp_patterns = ['*.tmp', '*.bak', '*.backup', '*~', '.DS_Store', 'Thumbs.db']
    removed = []
    
    for pattern in temp_patterns:
        for temp_file in PROJECT_ROOT.rglob(pattern):
            if temp_file.is_file() and '.venv' not in str(temp_file):
                temp_file.unlink(missing_ok=True)
                removed.append(str(temp_file.relative_to(PROJECT_ROOT)))
    
    if removed:
        print(f"✅ Đã xóa {len(removed)} temp files")
    else:
        print("✅ Không có temp files để xóa")


def clean_pytest_cache():
    """Xóa pytest cache."""
    cache_dirs = [
        PROJECT_ROOT / '.pytest_cache',
        PROJECT_ROOT / '.coverage',
        PROJECT_ROOT / 'htmlcov',
        PROJECT_ROOT / '.tox',
        PROJECT_ROOT / '.hypothesis',
    ]
    
    removed = []
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir, ignore_errors=True)
            else:
                cache_dir.unlink(missing_ok=True)
            removed.append(cache_dir.name)
    
    if removed:
        print(f"✅ Đã xóa {len(removed)} test cache files/dirs")
        for r in removed:
            print(f"   - {r}")
    else:
        print("✅ Không có test cache để xóa")


def main():
    """Main function."""
    print("🧹 Bắt đầu clean dự án...\n")
    
    clean_pycache()
    clean_pyc_files()
    clean_logs()
    clean_temp_files()
    clean_pytest_cache()
    
    print("\n✅ Hoàn thành clean dự án!")


if __name__ == "__main__":
    main()

