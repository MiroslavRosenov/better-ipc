import ast
import re

import setuptools
from pathlib import Path

with open("requirements.txt") as stream:
    raw = stream.read().splitlines()
    requirements = [x for x in raw if not x.startswith("git+")]
    dependencies = [x for x in raw if x.startswith("git+")]

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('discord/ext/ipc/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))

setuptools.setup(
    author="DaPandaOfficial",
    python_requires=">=3.8.0",
    license="Apache Software License",
    author_email="miroslav.rosenov39@gmail.com",
    long_description_content_type="text/markdown",
    url="https://github.com/MiroslavRosenov/better-ipc",
    description="A high-performance inter-process communication library designed to work with the latest version of discord.py",
    packages=[
        "discord.ext.ipc"
    ],
    project_urls={
        "Source": "https://github.com/MiroslavRosenov/better-ipc",
        "Issue Tracker": "https://github.com/MiroslavRosenov/better-ipc/issues",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Communications",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=["better-ipc", "ipc", "python", "discord.py"],
    long_description=long_description,
    install_requires=requirements,
    dependencies=dependencies,
    name="better-ipc",
    version=version,
)
