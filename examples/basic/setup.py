from distutils.core import setup
from pathlib import Path
from main import spam

setup(
   name='SpamPkg',
   version='1.0',
   ext_modules=[spam.as_extension(Path('/dev/shm/spam_pkg'))]
)
