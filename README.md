# Asynchronous Jobs

## Run locally

python app.py

or use vscode debugger

## Publish new version

1. From devcontainer build app package:

        make build

2. From outside of devcontainer build and pub a docker image:

        make docker-pub TAG=0.0.1
