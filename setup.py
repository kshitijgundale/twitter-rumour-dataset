from setuptools import setup

REQUIREMENTS = [
    "google",
    "newspaper3k",
    "snscrape",
    "inflect",
    "twython"
]
    
setup(name='avnio-scoring-autosklearn',
      version='1.0.0',
      description='Scripts for collecting context based rumour detection dataset from twitter. Uses snscrape',
      url='https://github.com/kshitijgundale/twitter-rumour-dataset',
      author='Kshitij Gundale',
      author_email='kshitijgundale08@gmail.com',
      license='MIT',
      packages=setuptools.find_packages(),
      install_requires=REQUIREMENTS,
)