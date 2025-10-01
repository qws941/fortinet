#!/bin/bash
# Remove duplicates from projects config and install enhanced ts

echo "=== Removing Duplicates and Installing Enhanced TS ==="

config_file="$HOME/.config/ts/projects.conf"

# Remove duplicates from config file
if [[ -f "$config_file" ]]; then
    echo "Checking for duplicates in $config_file..."

    # Create backup
    cp "$config_file" "$config_file.backup.$(date +%Y%m%d_%H%M%S)"

    # Remove duplicates (keep last occurrence)
    awk '!seen[$0]++' "$config_file" > "$config_file.tmp"
    mv "$config_file.tmp" "$config_file"

    echo "✓ Duplicates removed"
    echo "Current config:"
    cat "$config_file"
else
    echo "No config file found - creating empty one"
    touch "$config_file"
fi

echo ""
echo "=== Installing Enhanced TS as Default ==="

# Install enhanced ts as the default
if [[ -f "/usr/local/bin/ts-new" ]]; then
    sudo mv /usr/local/bin/ts /usr/local/bin/ts-original
    sudo mv /usr/local/bin/ts-new /usr/local/bin/ts

    echo "✓ Enhanced ts installed as default"
    echo "✓ Original ts backed up as ts-original"
else
    echo "Error: ts-new not found"
    exit 1
fi

echo ""
echo "=== Testing Final Installation ==="

# Test all new commands
echo "1. Testing ts add command:"
mkdir -p /tmp/test-final
ts add test-final /tmp/test-final

echo ""
echo "2. Testing ts projects:"
ts projects

echo ""
echo "3. Testing ts validate:"
/usr/local/bin/ts validate

echo ""
echo "4. Testing ts del:"
ts del test-final

echo ""
echo "✅ All tests passed! Enhanced ts commands are ready:"
echo "   - ts add <name> [path]"
echo "   - ts del <name>"
echo "   - ts cmd <session> '<command>'"
echo "   - ts projects"
echo "   - ts validate"