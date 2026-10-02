from setuptools import setup, find_packages

setup(
    name="cliagent",
    version="1.0.0",
    description="Intelligent File & Folder Management CLI Agent",
    packages=find_packages(),
    py_modules=["main", "config"],
    install_requires=[
        "rich>=13.0.0",
        "inquirerpy>=0.3.4",
        "rapidfuzz>=3.0.0",
        "httpx>=0.24.0",
        "typer>=0.9.0",
        "prompt_toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "autobot=main:main_launcher",
            "cliagent=main:main_launcher",
        ],
    },
    python_requires=">=3.10",
)
