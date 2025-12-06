#!/bin/bash
# 1. Download the setup script for Node.js 18 (stable)
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -

# 2. Install Node.js
apt-get install -y nodejs

# 3. Verify it worked (should print a version number like v18.x.x)
node -v