import json
from webservice import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2))
    exit(0)
