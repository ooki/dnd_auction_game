from pathlib import Path
from setuptools import setup


this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


__version__ = "0.3.0"

setup(
    name="dnd_auction_game",
    version=__version__,
    author="Sondre 'Ooki' Glimsdal",
    author_email="sondre.glimsdal@gmail.com",
    url="https://github.com/ooki/dnd_auction_game",
    project_urls= {
        "Bug Tracker": "https://github.com/ooki/dnd_auction_game/issues",
        "Documentation": "https://github.com/ooki/dnd_auction_game",
        "Source Code": "https://github.com/ooki/dnd_auction_game",
    },
    description="An auction game for trading-bots based on d&d die rolls.",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",        
        "Programming Language :: Python :: 3.9",
    ],
    license='MIT',
    long_description=long_description,
    long_description_content_type='text/markdown',
    zip_safe=False,
    python_requires=">=3.8",
    packages=['dnd_auction_game'],
    install_requires=[
          'py-machineid>=0.4.5',
          'fastapi',
          'uvicorn',
          'websockets',
          'Jinja2'
      ],
)

