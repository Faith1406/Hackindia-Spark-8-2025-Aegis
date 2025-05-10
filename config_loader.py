import json
import yaml
import os
import re
from dotenv import load_dotenv

load_dotenv()

env_var_pattern = re.compile(r'\$\{([^}^{]+)\}')

def resolve_env_variables(config):
    if isinstance(config, dict):
        return {k: resolve_env_variables(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [resolve_env_variables(item) for item in config]
    elif isinstance(config, str):
        matches = env_var_pattern.findall(config)
        for var in matches:
            value = os.getenv(var, "")
            config = config.replace(f"${{{var}}}", value)
        return config
    else:
        return config

def load_config(path="config.json"):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as f:
        if ext == ".json":
            raw_config = json.load(f)
        elif ext in ['.yaml', 'yml']:
            raw_config = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config file format: {ext}")
    
    return resolve_env_variables(raw_config)

