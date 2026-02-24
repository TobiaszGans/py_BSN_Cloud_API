from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bsn-cloud-api",
    version="1.1.0",
    author="Tobiasz Gans",
    author_email="tobgan@icloud.com",
    description="A comprehensive Python library for the BrightSign Network (BSN) Cloud API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TobiaszGans/py_BSN_Cloud_API",
    project_urls={
        "Bug Tracker": "https://github.com/TobiaszGans/py_BSN_Cloud_API/issues",
        "Documentation": "https://docs.brightsign.biz/developers/cloud-apis",
        "Source Code": "https://github.com/TobiaszGans/py_BSN_Cloud_API",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware",
        "Topic :: Multimedia :: Video :: Display",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.25.0",
        "python-dotenv>=0.19.0",
    ],
    keywords="brightsign bsn cloud api digital signage remote control",
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=3.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.950",
        ],
    },
)
