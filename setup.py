import glob

from Cython.Build import cythonize
from setuptools import Extension, setup

# 仅指定 'llm' 文件夹中的 Python 文件
files = glob.glob("llm/**/*.py", recursive=True)

extensions = [
    Extension(name=f.replace(".py", "").replace("/", "."), sources=[f]) for f in files
]

setup(
    name="llm-web-api",
    ext_modules=cythonize(extensions, build_dir="build/source", language_level="3"),
    script_args=["build_ext", "--build-lib", "build/dist"],
)
