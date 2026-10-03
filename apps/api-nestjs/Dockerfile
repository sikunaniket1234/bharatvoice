FROM node:24-alpine
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/api-nestjs/package.json apps/api-nestjs/package.json
COPY apps/web-angular/package.json apps/web-angular/package.json
RUN npm ci
COPY apps/api-nestjs apps/api-nestjs
CMD ["npm", "run", "api:dev"]
