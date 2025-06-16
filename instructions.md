I want to create a REST interface for the storyteller functionality using FastAPI.

For now, put all the service code in ./webservice.py

Initial resources:

* POST /stories - post body is empty. create a new story. Returns a redirect to /story/{uuid} where the uuid is the unique identifier for the story
* GET /stories/{uuid} - get the full story state
* POST /stories/{uuid} - posts a command as defined below. Returns JSON.

Command structure:

{ "command": "{name of command}", "body": "{optional body of command} }