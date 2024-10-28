#!/usr/bin/env bash

mkdir -p /workspaces/jobs/.vscode
cp /workspaces/jobs/.devcontainer/vscode/* /workspaces/jobs/.vscode

make bootstrap
