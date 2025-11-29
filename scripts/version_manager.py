#!/usr/bin/env python3
"""Version manager script for Smart E-Parking system."""

import json
import os
import subprocess
import sys
from pathlib import Path

VERSIONS = {
    "1.0": {
        "name": "MVP",
        "description": "Minimum Viable Product - Basic hardware and web dashboard",
        "dependencies": ["Flask>=3.0.0", "pyserial>=3.5", "python-dotenv>=1.0.1"],
        "features": [
            "Hardware Integration",
            "Serial Communication",
            "Basic Web Dashboard",
            "State Management"
        ]
    },
    "2.0": {
        "name": "Authentication",
        "description": "User authentication and role-based access",
        "dependencies": [
            "Flask>=3.0.0",
            "pyserial>=3.5",
            "python-dotenv>=1.0.1",
            "Flask-SQLAlchemy>=3.1.1",
            "Flask-Login>=0.6.3",
            "Flask-WTF>=1.2.1",
            "WTForms>=3.1.1",
            "Werkzeug>=3.0.1"
        ],
        "features": [
            "User Authentication",
            "Role-based Access",
            "User Management",
            "Session Management"
        ]
    },
    "3.0": {
        "name": "Sessions & Modes",
        "description": "Parking session management and operation modes",
        "dependencies": [
            "Flask>=3.0.0",
            "pyserial>=3.5",
            "python-dotenv>=1.0.1",
            "Flask-SQLAlchemy>=3.1.1",
            "Flask-Login>=0.6.3",
            "Flask-WTF>=1.2.1",
            "WTForms>=3.1.1",
            "Werkzeug>=3.0.1"
        ],
        "features": [
            "Parking Session Management",
            "AUTO/MANUAL Operation Modes",
            "Manual Control",
            "Session History"
        ]
    },
    "4.0": {
        "name": "Pricing & Payment",
        "description": "Flexible pricing system and payment tracking",
        "dependencies": [
            "Flask>=3.0.0",
            "pyserial>=3.5",
            "python-dotenv>=1.0.1",
            "Flask-SQLAlchemy>=3.1.1",
            "Flask-Login>=0.6.3",
            "Flask-WTF>=1.2.1",
            "WTForms>=3.1.1",
            "Werkzeug>=3.0.1"
        ],
        "features": [
            "Flexible Pricing Rules",
            "Fee Calculation",
            "Payment Management",
            "Pricing Admin Panel"
        ]
    },
    "5.0": {
        "name": "Production Ready",
        "description": "Advanced features and production deployment",
        "dependencies": [
            "Flask>=3.0.0",
            "pyserial>=3.5",
            "python-dotenv>=1.0.1",
            "Flask-SQLAlchemy>=3.1.1",
            "Flask-Login>=0.6.3",
            "Flask-WTF>=1.2.1",
            "WTForms>=3.1.1",
            "Werkzeug>=3.0.1",
            "gunicorn>=21.0.0"
        ],
        "features": [
            "Reports & Analytics",
            "Notifications",
            "API Documentation",
            "Production Deployment",
            "System Monitoring"
        ]
    }
}

CURRENT_VERSION = "4.0"


def print_version_info(version: str):
    """Print information about a version."""
    if version not in VERSIONS:
        print(f"❌ Version {version} không tồn tại!")
        print(f"📦 Các version có sẵn: {', '.join(VERSIONS.keys())}")
        return

    info = VERSIONS[version]
    print(f"\n📦 VERSION {version} - {info['name']}")
    print("=" * 60)
    print(f"📝 Mô tả: {info['description']}")
    print(f"\n✨ Tính năng:")
    for feature in info['features']:
        print(f"  • {feature}")
    print(f"\n📚 Dependencies:")
    for dep in info['dependencies']:
        print(f"  • {dep}")


def list_versions():
    """List all available versions."""
    print("\n📦 CÁC VERSION CÓ SẴN:")
    print("=" * 60)
    for version, info in VERSIONS.items():
        current_marker = " (CURRENT)" if version == CURRENT_VERSION else ""
        print(f"\n{version} - {info['name']}{current_marker}")
        print(f"  {info['description']}")


def generate_requirements(version: str, output_file: str = "requirements.txt"):
    """Generate requirements.txt for a specific version."""
    if version not in VERSIONS:
        print(f"❌ Version {version} không tồn tại!")
        return False

    deps = VERSIONS[version]['dependencies']
    
    # Thêm RPi.GPIO cho Raspberry Pi (optional)
    if os.name != 'nt':  # Not Windows
        deps.append("RPi.GPIO>=0.7.1")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for dep in deps:
            f.write(f"{dep}\n")
    
    print(f"✅ Đã tạo {output_file} cho version {version}")
    return True


def check_current_version():
    """Check and display current version."""
    print(f"\n🎯 VERSION HIỆN TẠI: {CURRENT_VERSION}")
    print_version_info(CURRENT_VERSION)


def create_version_tag(version: str):
    """Create a Git tag for a version."""
    if version not in VERSIONS:
        print(f"❌ Version {version} không tồn tại!")
        return False

    try:
        # Check if git is available
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        
        # Check if we're in a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("⚠️  Không phải Git repository. Bỏ qua tạo tag.")
            return False

        info = VERSIONS[version]
        tag_name = f"v{version}"
        message = f"Release {version} - {info['name']}: {info['description']}"
        
        # Create tag
        subprocess.run(
            ["git", "tag", "-a", tag_name, "-m", message],
            check=True
        )
        
        print(f"✅ Đã tạo Git tag: {tag_name}")
        print(f"💡 Để push tag lên remote: git push origin {tag_name}")
        return True
        
    except subprocess.CalledProcessError:
        print("⚠️  Git không khả dụng hoặc không phải Git repo.")
        return False
    except FileNotFoundError:
        print("⚠️  Git không được cài đặt.")
        return False


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("\n🚀 SMART E-PARKING - VERSION MANAGER")
        print("=" * 60)
        print("\nCách sử dụng:")
        print("  python scripts/version_manager.py list              # Liệt kê tất cả versions")
        print("  python scripts/version_manager.py info <version>    # Xem thông tin version")
        print("  python scripts/version_manager.py current            # Xem version hiện tại")
        print("  python scripts/version_manager.py generate <version> # Tạo requirements.txt cho version")
        print("  python scripts/version_manager.py tag <version>      # Tạo Git tag cho version")
        print("\nVí dụ:")
        print("  python scripts/version_manager.py info 2.0")
        print("  python scripts/version_manager.py generate 1.0")
        return

    command = sys.argv[1].lower()

    if command == "list":
        list_versions()
        check_current_version()

    elif command == "info":
        if len(sys.argv) < 3:
            print("❌ Thiếu tham số version!")
            print("   Sử dụng: python scripts/version_manager.py info <version>")
            return
        version = sys.argv[2]
        print_version_info(version)

    elif command == "current":
        check_current_version()

    elif command == "generate":
        if len(sys.argv) < 3:
            print("❌ Thiếu tham số version!")
            print("   Sử dụng: python scripts/version_manager.py generate <version>")
            return
        version = sys.argv[2]
        generate_requirements(version)

    elif command == "tag":
        if len(sys.argv) < 3:
            print("❌ Thiếu tham số version!")
            print("   Sử dụng: python scripts/version_manager.py tag <version>")
            return
        version = sys.argv[2]
        create_version_tag(version)

    else:
        print(f"❌ Lệnh không hợp lệ: {command}")
        print("   Sử dụng: python scripts/version_manager.py list")


if __name__ == "__main__":
    main()

