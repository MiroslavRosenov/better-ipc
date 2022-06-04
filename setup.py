import re
import setuptools

classifiers = [
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
]

with open("requirements.txt") as stream:
    raw = stream.read().splitlines()

    requirements = [x for x in raw if not x.startswith("git+")]
    dependencies = [x for x in raw if x.startswith("git+")]

packages = [
    "discord.ext.ipc",
]

project_urls = {
    "Source": "https://github.com/MiroslavRosenov/better-ipc",
    "Issue Tracker": "https://github.com/MiroslavRosenov/better-ipc/issues",
}

_version_regex = r"^version = ('|\")((?:[0-9]+\.)*[0-9]+(?:\.?([a-z]+)(?:\.?[0-9])?)?)\1$"

with open("discord/ext/ipc/__init__.py") as stream:
    match = re.search(_version_regex, stream.read(), re.MULTILINE)

version = match.group(2)

setuptools.setup(
    name="better-ipc",
    author="DaPandaOfficial",
    author_email="miroslav.rosenov39@gmail.com",
    classifiers=classifiers,
    description="IPC for discord.py",
    long_description="A high-performance inter-process communication library designed to work with the latest version of discord.py",
    install_requires=requirements,
    dependency_links=dependencies,
    license="Apache Software License",
    packages=packages,
    project_urls=project_urls,
    python_requires=">=3.8.0",
    url="https://github.com/MiroslavRosenov/better-ipc",
    download_url="https://github.com/MiroslavRosenov/better-ipc/archive/refs/tags/1.0.tar.gz",
    version=version,
)
