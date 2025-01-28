# File: ~/frappe-bench/apps/plantbot/setup.py

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="plantbot",
    version="0.0.1",
    description="Plantbot - Chatbot for Plantrich Agritech",
    author="vinay",  # Update with your actual name
    author_email="reddysrivinayofficial@gmail.com",  # Update with your actual email
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)