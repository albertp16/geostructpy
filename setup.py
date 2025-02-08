from setuptools import setup, find_packages

setup(
    name='geostructpy',
    version='0.1',
    description='This APEC internal use only for Geotechnical - Structural libraries',
    author='Albert Pamonag',
    author_email='albert@apeconsultancy.net',
    url='https://github.com/albertp16/geostructpy',
    packages=find_packages(),
    install_requires=[
        'matplotlib'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    company='Albert Pamonag Engineering Consultancy',
)