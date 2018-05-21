import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ipymap",
    version="0.0.1",
    author="Yuan \"Forrest\" Yu",
    author_email="yy@yuyuan.org",
    description="mapping tool in jupyter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yyu/ipymap",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
