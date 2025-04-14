from setuptools import find_packages, setup

# Read the README for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="onvifscout",
    # Remove hardcoded version - will be managed by CI
    use_scm_version={
        "version_scheme": "post-release",
        "local_scheme": "dirty-tag",
    },
    description="A comprehensive ONVIF device discovery and analysis tool for network cameras and devices",  # noqa: E501
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Chriss Martin",
    url="https://github.com/chrissmartin/onvifscout",
    project_urls={
        "Bug Tracker": "https://github.com/chrissmartin/onvifscout/issues",
        "Documentation": "https://github.com/chrissmartin/onvifscout",
        "Source Code": "https://github.com/chrissmartin/onvifscout",
    },
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "colorama>=0.4.6",
        "requests>=2.32.3",
        "pillow>=10.0.0",
        "urllib3>=2.2.3",
    ],
    setup_requires=["setuptools_scm"],
    entry_points={
        "console_scripts": [
            "onvifscout=onvifscout.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: Security",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="onvif camera network security monitoring discovery ip-camera cctv surveillance",  # noqa: E501
)
