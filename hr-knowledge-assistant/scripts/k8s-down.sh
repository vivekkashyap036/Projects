#!/usr/bin/env bash
# Delete the whole local cluster (and everything in it).
set -euo pipefail
kind delete cluster --name hr-assistant
