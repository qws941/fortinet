#!/bin/bash
echo "=== TS Master Quick Test ==="
echo ""

echo "1. Version check:"
/usr/local/bin/ts version | head -3

echo ""
echo "2. List sessions:"
/usr/local/bin/ts list | head -5

echo ""
echo "3. Background task test:"
/usr/local/bin/ts bg list

echo ""
echo "4. Help command:"
/usr/local/bin/ts help | head -10

echo ""
echo "✓ All quick tests completed!"
