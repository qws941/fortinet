FROM node:20-alpine

# Install tmux
RUN apk add --no-cache tmux

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY src/ ./src/

# Expose ports
EXPOSE 3000 3001

# Start server
CMD ["node", "src/index.js"]
