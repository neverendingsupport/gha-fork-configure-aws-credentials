# Use a lightweight Node.js image
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json to install dependencies
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of your action's code
COPY src/ ./src/

COPY THIRD-PARTY ./
COPY tsconfig.json ./
RUN npm run package

WORKDIR /app/dist

# Define the entrypoint for your action
# This will be the command executed when the container starts
ENTRYPOINT ["node", "index.js"]
