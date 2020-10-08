#!/bin/bash

# Set namespace
sed -i "s/karvdash\-namespace/${KARVDASH_NAMESPACE}/" /zeppelin/conf/interpreter.json

# Run Zeppelin
/zeppelin/bin/zeppelin.sh
