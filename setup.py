from setuptools import setup, find_packages

setup(
    name='aioldsplice',
    version='0.0.1',
    description='asyncio splicing socket proxy',
    url='http://github.com/drie/aioldsplice',
    author='Tom van Neerijnen',
    author_email='tom@tomvn.com',
    keywords='proxy splice socket',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
    ],
    packages=find_packages(exclude=['tests*']))
