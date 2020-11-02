import ast
import io
import re

from setuptools import setup, find_packages

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

_description_re = re.compile(r"description\s+=\s+(?P<description>.*)")

with open("lektor_shortcodes.py", "rb") as f:
    description = str(
        ast.literal_eval(_description_re.search(f.read().decode("utf-8")).group(1))
    )

setup(
    author="Ian Castleden,,,",
    author_email="ian.castleden@gmail.com",
    description=description,
    keywords="Lektor plugin",
    license="MIT",
    long_description=readme,
    long_description_content_type="text/markdown",
    name="lektor-shortcodes",
    packages=find_packages(),
    py_modules=["lektor_shortcodes"],
    url="https://github.com/arabidopsis/lektor-shortcodes",
    version="0.1",
    classifiers=["Framework :: Lektor", "Environment :: Plugins",],
    entry_points={
        "lektor.plugins": ["shortcodes = lektor_shortcodes:ShortcodesPlugin",]
    },
)
