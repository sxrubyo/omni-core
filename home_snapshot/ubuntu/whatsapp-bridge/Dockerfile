FROM node:22-slim
RUN apt-get update && apt-get install -y python3 make g++ git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY index.js ./
ENV PORT=3000 SESSION_DIR=/app/sessions/default WEBHOOK_URL="" PHONE_NUMBER="" LOG_LEVEL=info
EXPOSE 3000
CMD ["node", "index.js"]
