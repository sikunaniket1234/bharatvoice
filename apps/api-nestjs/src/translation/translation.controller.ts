import { Body, Controller, Post } from '@nestjs/common';
import { TranslationRequestDto, TranslationResponseDto } from './translation.dto';
import { TranslationService } from './translation.service';

@Controller('translation')
export class TranslationController {
  constructor(private readonly translationService: TranslationService) {}

  @Post()
  translate(@Body() request: TranslationRequestDto): Promise<TranslationResponseDto> {
    return this.translationService.translate(request);
  }
}
