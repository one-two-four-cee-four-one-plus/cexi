import setuptools

setuptools.setup(
    name="cexi",
    version="0.0.1",
    author="melvin kaye",
    author_email="one.two.four.cee.four.one.plus@gmail.com",
    description="Cee EXtensions Interpolation",
    url="https://github.com/one-two-four-cee-four-one-plus/cexi",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.9",
)
