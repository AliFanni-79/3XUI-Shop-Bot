import warnings

# Filter non-breaking deprecation warnings from test dependencies (FastAPI / Starlette testclient)
warnings.filterwarnings("ignore", category=DeprecationWarning)
