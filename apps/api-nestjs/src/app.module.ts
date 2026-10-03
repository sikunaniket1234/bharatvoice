import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { HealthController } from './health.controller';
import { TranslationController } from './translation/translation.controller';
import { TranslationService } from './translation/translation.service';

@Module({
  imports: [ConfigModule.forRoot({ isGlobal: true })],
  controllers: [HealthController, TranslationController],
  providers: [TranslationService],
})
export class AppModule {}
