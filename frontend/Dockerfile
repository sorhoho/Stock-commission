FROM node:20-slim AS builder
WORKDIR /app
ENV NODE_TLS_REJECT_UNAUTHORIZED=0 \
    NPM_CONFIG_STRICT_SSL=false
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
