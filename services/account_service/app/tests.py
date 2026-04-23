import os

from django.test import TestCase
from django.conf import settings
from decouple import config

# Create your tests here.
t=config("DEBUG", default="true").lower() == "true"
print("DEBUG:", t)