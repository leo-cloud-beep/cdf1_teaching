"""

Intro to project ...


Setup
=====

In order to use this library, ...


Main concepts
=============

Describe typical classes found in project

.. autoclass:: SampleClassName
   :members:


"""

from .geometry_basics import *
from .algorithms import *
from .bismuth_crystal import *

# If you add a new python file...

__all__ = []

from .bismuth_crystal import (
    create_seed,
    grow_hoppers,
    add_branches,
    make_meshes,
    make_colors,
    pack,
    unpack,
)

