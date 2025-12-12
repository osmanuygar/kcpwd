from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="kcpwd",
    version="0.8.1",
    author="osmanuygar",
    author_email="osmanuygar@gmail.com",
    description="Cross-platform Password Manager with Web UI & Kubernetes Integration - Works everywhere! macOS Keychain, Linux Secret Service, Windows Credential Locker, or encrypted file storage. Native K8s secret sync, Helm integration, zero dependencies required.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/osmanuygar/kcpwd",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "Topic :: Security",
        "Topic :: Security :: Cryptography",
        "Topic :: Utilities",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: Microsoft :: Windows :: Windows 11",
        "Environment :: Console",
        "Environment :: Web Environment",
    ],
    keywords="password manager cli keychain macos linux windows security decorator library import export backup master-password encryption cross-platform web-ui fastapi credential-locker kubernetes k8s helm secret-management devops gitops argocd flux cicd",
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "keyring>=23.0.0",
        "cryptography>=41.0.0",
        "secretstorage>=3.3.0; sys_platform == 'linux'",
        "pywin32>=305; sys_platform == 'win32'",
        "pyyaml>=6.0.0",  # For Helm integration
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "build>=0.10.0",
            "twine>=4.0.0",
            "cryptography>=41.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.7.0",
            "httpx>=0.25.0",
        ],
        "ui": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.0.0",
            "python-multipart>=0.0.6",
        ]
    },
    entry_points={
        "console_scripts": [
            "kcpwd=kcpwd.cli:cli",
        ],
    },
    # Include static files
    package_data={
        "kcpwd": [
            "ui/static/*.html",
            "ui/static/*.css",
            "ui/static/*.js",
            "ui/static/*.png",
        ],
    },
    include_package_data=True,
)