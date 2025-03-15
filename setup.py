from setuptools import setup, find_packages

def read_requirements(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

setup(
    name='sync_notion2anki',
    version='1.0.0',
    py_modules=['sync_notion2anki'],
    install_requires=read_requirements('requirements.txt'),
    entry_points={
        'console_scripts': [
            'sync_notion2anki = sync_notion2anki:main',
        ],
    },
)

