#!/usr/bin/env bash

OGEDITOR=${EDITOR}

export EDITOR='open -a "Zed Preview"'

ansible-vault edit service_conf.yaml

export EDITOR=${OGEDITOR}
