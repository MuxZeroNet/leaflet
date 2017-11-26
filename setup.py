from setuptools import setup, find_packages

setup(
    name='leaflet',
    version='0.0.3',

    description='Dead simple I2P SAM library',
    long_description=open('README.rst').read(),
    url='https://github.com/MuxZeroNet/leaflet',

    author='MuxZeroNet',
    author_email='muxzeronet@users.noreply.github.com',

    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
    ],
    keywords='I2P SAM socket',

    packages=['leaflet', 'leaflet.examples'],
    python_requires='>=3'
)

