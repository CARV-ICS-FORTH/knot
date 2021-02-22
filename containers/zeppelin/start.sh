#!/bin/bash

# Set namespace
sed -i "s/karvdash\-namespace/${KARVDASH_NAMESPACE}/" /opt/zeppelin/conf/interpreter.json

# Run Zeppelin
/opt/zeppelin/bin/zeppelin.sh
