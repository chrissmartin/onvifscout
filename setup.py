from setuptools import setup, find_packages

setup(
    name="onvifscout",
    version="1.0.0",
    description="A comprehensive ONVIF device discovery and analysis tool",
    author="Chriss Martin",
    author_email="thechrissmartin@gmail.com",
    packages=find_packages(),
    install_requires=[
        "colorama>=0.4.6",
        "requests>=2.32.3",
    ],
    entry_points={
        "console_scripts": [
            "onvifscout=onvifscout.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
)
