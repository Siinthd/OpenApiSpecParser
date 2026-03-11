from setuptools import setup, find_packages

'''
def readme():
  with open('README.md', 'r', encoding='utf-8') as f:
    return f.read()
'''

setup(
    name='REST2JSON',
    version='0.0.5',
    author='Denis Kodolich',
    author_email='d.kodolich@concept-software.ru',
    description='metadriven-адаптер для RESTAPI запросов',
    
    # ВАЖНО: ищем пакеты в папке src
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    
    # Явно указываем, что включать
    package_data={
        'REST2JSON': ['*/*.py', '*.py'],
    },
    
    install_requires=[
        'httpx>=0.24.0',
        'omegaconf>=2.3.0',
        'pyyaml>=6.0',
    ],
    python_requires='>=3.8',
)