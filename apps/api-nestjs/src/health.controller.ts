import { Controller, Get } from '@nestjs/common';

@Controller()
export class HealthController {
  @Get('health')
  health(): { status: string; service: string } {
    return { status: 'ok', service: 'api-nestjs' };
  }
}
