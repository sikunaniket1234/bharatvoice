import { Transform } from 'class-transformer';
import { IsIn, IsString, Length } from 'class-validator';

export const LANGUAGE_CODES = ['en', 'or', 'hi'] as const;
export type LanguageCode = (typeof LANGUAGE_CODES)[number];

export class TranslationRequestDto {
  @Transform(({ value }) => (typeof value === 'string' ? value.trim() : value))
  @IsString()
  @Length(1, 5000)
  text!: string;

  @IsIn(LANGUAGE_CODES)
  source_language!: LanguageCode;

  @IsIn(LANGUAGE_CODES)
  target_language!: LanguageCode;
}

export interface TranslationResponseDto {
  translated_text: string;
  source_language: LanguageCode;
  target_language: LanguageCode;
  model_name: string;
  model_version: string;
}
