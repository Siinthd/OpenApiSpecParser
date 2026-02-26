from setuptools import setup, find_packages

'''
def readme():
  with open('README.md', 'r', encoding='utf-8') as f:
    return f.read()
'''

setup(
  name='OpenAPISpecParser',
  version='0.0.1',  
  author='Denis Kodolich',
  author_email='d.kodolich@concept-software.ru',
  description='Парсер OpenAPI спецификаций и адаптер для REST API запросов',
  long_description='',
  long_description_content_type='text/markdown',
  url='https://github.com/Siinthd/OpenApiSpecParser',
  packages=find_packages(where='src'),  
  package_dir={'': 'src'},  # Корневая директория для пакетов - src
  install_requires=[
    'httpx>=0.24.0',      
    'omegaconf>=2.3.0',   
    'pyyaml>=6.0',        
    'typing-extensions>=4.5.0'  
  ],
  classifiers=[
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Internet :: WWW/HTTP',
  ],
  keywords='openapi swagger rest api client parser adapter',
  project_urls={
    'GitHub': 'https://github.com/Siinthd/OpenApiSpecParser',
    'Bug Tracker': 'https://github.com/Siinthd/OpenApiSpecParser/issues',
  },
  python_requires='>=3.8',
  include_package_data=True,  # Включает файлы из MANIFEST.in
  zip_safe=False,  # Позволяет установку в режиме разработки
)