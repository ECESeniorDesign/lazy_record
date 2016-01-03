from distutils.core import setup
setup(
  name = 'lazy_record',
  packages = ['lazy_record', 'lazy_record/base'], # this must be the same as the name above
  version = '0.1.1.dev',
  description = 'Generic Model Layer for Python Web Applications using Sqlite3',
  author = 'Chase Conklin',
  author_email = 'cconkli4@u.rochester.edu',
  url = 'https://github.com/ECESeniorDesign/lazy_record', # use the URL to the github repo
  download_url = 'https://github.com/ECESeniorDesign/lazy_record/tarball/0.1.1.dev', # I'll explain this in a second
  keywords = ['flask'],
  classifiers = [],
)