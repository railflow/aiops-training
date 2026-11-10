import numpy as np
import pandas as pd
import requests
from flask import Flask  # noqa: F401  (imported only to prove it is installed)

df = pd.DataFrame({"x": np.arange(3), "y": np.arange(3) ** 2})
print("Hello from python with", pd.__version__, "pandas and", np.__version__, "numpy")
print(df.to_string(index=False))
print("requests", requests.__version__)
