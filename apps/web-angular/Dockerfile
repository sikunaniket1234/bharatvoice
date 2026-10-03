FROM node:24-alpine AS build
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/api-nestjs/package.json apps/api-nestjs/package.json
COPY apps/web-angular/package.json apps/web-angular/package.json
RUN npm ci
COPY apps/web-angular apps/web-angular
RUN npm run web:build

FROM nginx:1.27-alpine
COPY apps/web-angular/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/web-angular/dist/web-angular/browser /usr/share/nginx/html
EXPOSE 80
