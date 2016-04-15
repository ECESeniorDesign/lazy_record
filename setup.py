from setuptools import setup
version = "0.6.0"
setup(
  name='lazy_record',
  packages=['lazy_record', 'lazy_record/base'],
  version=version,
  description='Generic Model Layer for Python Web Applications using Sqlite3',
  author='Chase Conklin',
  author_email='cconkli4@u.rochester.edu',
  url='https://github.com/ECESeniorDesign/lazy_record',
  download_url='https://github.com/ECESeniorDesign/'
               'lazy_record/tarball/' + version,
  keywords=['flask'],
  install_requires=[
    'inflector',
  ],
  classifiers=[],
)
