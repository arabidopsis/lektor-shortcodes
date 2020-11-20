from setuptools import find_packages, setup

with open("README.md", encoding="utf8") as f:
    readme = f.read()


# note that this does require requests
# but the way it is installed via lektor we don't need
# to specifiy it since lektor itself depends on it
setup(
    author="Ian Castleden",
    author_email="ian.castleden@gmail.com",
    description="Embeds shortcodes in Markdown.",
    keywords="Lektor plugin",
    license="MIT",
    long_description=readme,
    long_description_content_type="text/markdown",
    name="lektor-shortcodes",
    packages=find_packages(),
    url="https://github.com/arabidopsis/lektor-shortcodes",
    version="0.1",
    classifiers=["Framework :: Lektor", "Environment :: Plugins"],
    entry_points={
        "lektor.plugins": ["shortcodes = lektor_shortcodes:ShortcodesPlugin"]
    },
)
