from setuptools import setup, find_packages


setup(
    name='wampyre',
    version='1.0.0',
    description='Python implementation of a WAMP router.',
    author='Anders Jensen',
    author_email='johndoee@tidalstream.org',
    url='https://github.com/JohnDoee/wampyre',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    extras_require={
        'django': [
            'channels',
            'autobahn',
        ],
        'tests': [
            'pytest',
        ],
    }
)
