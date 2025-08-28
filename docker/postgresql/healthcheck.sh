#!/bin/sh
# PostgreSQL health check script

pg_isready -U ${POSTGRES_USER:-fortinet} -d ${POSTGRES_DB:-fortinet}
exit $?