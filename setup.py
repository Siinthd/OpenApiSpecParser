from setuptools import setup, find_packages

def readme():
    with open('README.md', 'r', encoding='utf-8') as f:
        return f.read()

setup(
    name='REST2JSON',
    version='0.1.5',
    author='Denis Kodolich',
    author_email='d.kodolich@concept-software.ru',
    description='metadriven-адаптер для RESTAPI запросов',
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/Siinthd/REST2JSON',  # Добавьте ваш репозиторий
    
    # Классификаторы для PyPI
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],
    
    # ВАЖНО: ищем пакеты в папке src
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    
    # Явно указываем, что включать
    package_data={
        'REST2JSON': ['*.py', 'utils/*.py'], 
    },
    include_package_data=True,
    
    install_requires=[
        'httpx>=0.24.0',
        'omegaconf>=2.3.0',
        'pyyaml>=6.0',
        'requests>=2.28.0',
    ],
    
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'isort>=5.0.0',
            'mypy>=1.0.0',
        ],
        'docs': [
            'sphinx>=6.0.0',
            'sphinx-rtd-theme>=1.0.0',
        ],
    },
    
    python_requires='>=3.8',
    
    # Точки входа если нужно (для CLI)
    entry_points={
        'console_scripts': [
            # 'rest2json = REST2JSON.cli:main',  # если будет CLI
        ],
    },
    
    # Проектные URLs
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/REST2JSON/issues',
        'Source': 'https://github.com/yourusername/REST2JSON',
        'Documentation': 'https://REST2JSON.readthedocs.io',
    },
    
    zip_safe=False,  # Рекомендуется для пакетов с непитоновскими файлами
)
