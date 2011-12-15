from setuptools import setup, find_packages

setup(
    name = 'artemis',
    version = '0.3',
    packages = find_packages(),
    install_requires = [
        "Flask==0.7.2",
        "Flask-Login",
        "Flask-WTF",
        "pyes==0.16",
        "chardet",
				],
    url = 'http://cottagelabs.com/',
    author = 'Cottage Labs',
    author_email = 'us@cottagelabs.com',
    description = 'Artemis parts management system',
    license = 'AGPL',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)

