from setuptools import setup
setup(
  name='lazy_record',
  packages=['lazy_record', 'lazy_record/base'],
  version='0.5.2',
  description='Generic Model Layer for Python Web Applications using Sqlite3',
  author='Chase Conklin',
  author_email='cconkli4@u.rochester.edu',
  url='https://github.com/ECESeniorDesign/lazy_record',
  download_url='https://github.com/ECESeniorDesign/'
               'lazy_record/tarball/0.5.2',
  keywords=['flask'],
  install_requires=[
    'inflector',
  ],
  classifiers=[],
)
