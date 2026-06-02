#!/bin/bash
# Backward compatibility wrapper for install.sh
cd "$(dirname "$0")"
exec ./install.sh
