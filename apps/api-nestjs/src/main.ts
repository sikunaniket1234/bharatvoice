import 'reflect-metadata';
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);
  app.setGlobalPrefix('api/v1');
  app.useGlobalPipes(
    new ValidationPipe({
      transform: true,
      whitelist: true,
      forbidNonWhitelisted: true,
    }),
  );
  app.enableCors({ origin: process.env.WEB_ORIGIN ?? 'http://localhost:4200' });
  const port = Number(process.env.PORT ?? 3000);
  const host = process.env.API_HOST ?? '127.0.0.1';
  await app.listen(port, host);
}

void bootstrap();
