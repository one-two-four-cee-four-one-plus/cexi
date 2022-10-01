from sys import intern
from string import ascii_letters

TAB = intern("    ")
ALLOWED_CHARACTERS = set(ascii_letters) | set('_')
