from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

setup_args = generate_distutils_setup(
    packages=['child_safety_monitoring', 'child_safety_monitoring.core'],
    package_dir={'': 'src'},
)

setup(**setup_args)
