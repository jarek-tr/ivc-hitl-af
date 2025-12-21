"""
IVC HITL-AF: Image and Video Computing - Human-in-the-Loop Annotation Framework

A modular, production-ready annotation infrastructure for research datasets.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="ivc-hitl-af",
    version="0.1.0",
    description="Modular human-in-the-loop annotation framework for image and video datasets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Lab",
    author_email="lab@university.edu",
    url="https://github.com/yourlab/ivc-hitl-af",
    packages=find_packages(where="backend"),
    package_dir={"": "backend"},
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-django>=4.5",
            "black>=23.0",
            "flake8>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ivc-hitl-af=ivc_hitl_af.cli:main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Framework :: Celery",
    ],
    keywords="annotation machine-learning computer-vision mturk crowdsourcing research",
    project_urls={
        "Bug Reports": "https://github.com/yourlab/ivc-hitl-af/issues",
        "Documentation": "https://github.com/yourlab/ivc-hitl-af/tree/main/docs",
        "Source": "https://github.com/yourlab/ivc-hitl-af",
    },
)
