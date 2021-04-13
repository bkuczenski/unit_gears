from setuptools import setup, find_packages

requires = [
    'stats_arrays>=0.6.4',
    'synonym_dict>=0.1.1'
]

'''
VERSION HISTORY

1.0.4 - forgot master_gear_mapping.csv
1.0.3 - Added MANIFEST.in and included model library and docs

1.0.2 - Added automatic tabulation of models for SciAdv paper; released to PyPI

1.0.1 - 30 Mar 2021 - Py3.6 compatibility (prod)

1.0.0 - 30 Mar 2021 - Initial release with JIE Manuscript 

0.1.0 - 18 November 2020 - Initial setup 
'''

VERSION = '1.0.4'

setup(
    name="unit_gears",
    version=VERSION,
    author="Brandon Kuczenski",
    author_email="bkuczenski@ucsb.edu",
    license='BSD 3-clause',
    install_requires=requires,
    url="https://github.com/bkuczenski/unit_gears",
    description="A library of uncertain models for the industrial operation of fishing gears",
    long_description_content_type='text/markdown',
    long_description=open('README.md').read(),
    packages=find_packages(),
    include_package_data=True,
    package_data={'unit_gears': ['models/*.json', 'reference/*.json', 'reference/*.csv', 'templates/*.json']}
)
