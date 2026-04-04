from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='geostructpy',
    version='0.3.0',
    description='Geotechnical engineering toolkit for structural engineers',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Albert Pamonag',
    author_email='albert@apeconsultancy.net',
    url='https://github.com/albertp16/geostructpy',
    project_urls={
        'Documentation': 'https://github.com/albertp16/geostructpy/wiki',
        'Bug Reports': 'https://github.com/albertp16/geostructpy/issues',
    },
    packages=find_packages(),
    install_requires=[
        'matplotlib',
    ],
    python_requires='>=3.8',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
    ],
    keywords='geotechnical engineering bearing-capacity spt foundation micropile',
)
