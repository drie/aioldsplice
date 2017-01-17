from setuptools import setup, find_packages

setup(name='oldsplice',
    version='0.0.1',
    description='asyncio splice proxy for two sockets',
    url='http://github.com/tommyvn/oldsplice',
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
