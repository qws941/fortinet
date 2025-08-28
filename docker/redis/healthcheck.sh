#!/bin/sh
# Redis health check script

redis-cli ping | grep -q PONG
exit $?