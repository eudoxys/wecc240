"""Simulation utilities"""

import sys
import json

def _autocast(x):
    """Automatically cast a string to python object"""
    for dtype in ("basic","dict","list","str"):
        match dtype:
            case "basic":
                try:
                    return json.loads(x)
                except Exception as err:
                    pass
            case "dict":
                try:
                    if ":" in x:
                        items = x.split(",")
                        return {y:_autocast(z) for y,z in [v.split(":",1) for v in items]}
                except Exception as err:
                    pass
            case "list":
                try:
                    if "," in x:
                        return [_autocast(y) for y in x.split(",")]
                except Exception as err:
                    pass
            case "str":
                return str(x)
    raise ValueError(f"unable to autocast {x=}")

def getargs(args=None,flags=None,values=None,kwargs=None):
    """Get args, kwargs, flags, and values from argument list

    Extracts the various parts of the command line as follows.

    - `args` have no leading dash or equal sign embedded.

    - `kwargs` have a leading double dash. If an equal sign is embedded the
      item of kwargs is set to the value that follows the equal sign.
      Otherwise, the item is set to `True`.

    - `flags` have a single dash. The list entry is the value following the
      dash.

    - `values` have an equal sign embedded with no leading dash. The key is
      the portion before the equal sign and value is everything after the
      equal sign.

    Values are automatically converted to python values as follows.

    1. Basic values, i.e., `None`, `bool, `int`, `float` as interpreted by the
    JSON loader. Values in double-quotes are interpreted as `str`.

    2. Dictionaries, i.e., `key:value` comma-separated strings.

    3. Lists, i.e., comma-separated values.

    4. String, everything else is simply interpreted as a string.
    """

    # convert position arguments (not starting with a dash)
    if args is None:
        args = tuple(_autocast(x) for x in sys.argv[1:] if x[0] != "-" and "=" not in x)
    
    # convert keyword arguments (starting with double dash)
    if kwargs is None:
        kwargs = {}
        for value in (y[2:] for y in sys.argv[1:] if y.startswith("--")):
            if "=" in value:
                key,value = value.split("=",1)
                kwargs[key] = _autocast(value)
            else:
                kwargs[value] = True
    
    # convert flags (starting with single dash)
    if flags is None:
        flags = tuple(x[1:] for x in sys.argv[1:] if x[0]=="-" and x[1] != "-")
    
    # values (no leading dash but has equal sign)
    if values is None:
        values = {}
        for key,value in (x.split("=",1) for x in sys.argv[1:] if "=" in x and not x.startswith("-")):
            values[key] = _autocast(value)

    return args,kwargs,flags,values
