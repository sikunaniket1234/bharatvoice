import {
  BadGatewayException,
  BadRequestException,
  Injectable,
  ServiceUnavailableException,
} from '@nestjs/common';
import {
  LanguageCode,
  TranslationRequestDto,
  TranslationResponseDto,
} from './translation.dto';

const SUPPORTED_PAIRS = new Set(['en:or', 'or:en', 'en:hi', 'hi:en']);

function isTranslationResponse(value: unknown): value is TranslationResponseDto {
  if (typeof value !== 'object' || value === null) return false;
  const result = value as Record<string, unknown>;
  return (
    typeof result.translated_text === 'string' &&
    typeof result.model_name === 'string' &&
    typeof result.model_version === 'string' &&
    ['en', 'or', 'hi'].includes(String(result.source_language)) &&
    ['en', 'or', 'hi'].includes(String(result.target_language))
  );
}

@Injectable()
export class TranslationService {
  async translate(request: TranslationRequestDto): Promise<TranslationResponseDto> {
    const pair = `${request.source_language}:${request.target_language}`;
    if (!SUPPORTED_PAIRS.has(pair)) {
      throw new BadRequestException({
        code: 'unsupported_language_pair',
        message: 'Phase 1 supports English ↔ Odia and English ↔ Hindi only.',
      });
    }

    const baseUrl = (process.env.AI_SERVICE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
    let response: Response;
    try {
      response = await fetch(`${baseUrl}/api/v1/translation`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(request),
        signal: AbortSignal.timeout(15_000),
      });
    } catch {
      throw new ServiceUnavailableException({
        code: 'ai_service_unavailable',
        message: 'The private AI service could not be reached.',
      });
    }

    const responseText = await response.text();
    if (!response.ok) {
      if (response.status === 503) {
        throw new ServiceUnavailableException(this.parseError(responseText));
      }
      throw new BadGatewayException({
        code: 'ai_service_error',
        message: 'The AI service rejected or could not complete the translation request.',
      });
    }

    let result: unknown;
    try {
      result = JSON.parse(responseText);
    } catch {
      throw new BadGatewayException({
        code: 'invalid_ai_response',
        message: 'The AI service returned an invalid response.',
      });
    }
    if (
      !isTranslationResponse(result) ||
      result.source_language !== (request.source_language as LanguageCode) ||
      result.target_language !== (request.target_language as LanguageCode)
    ) {
      throw new BadGatewayException({
        code: 'invalid_ai_response',
        message: 'The AI service response did not match the translation contract.',
      });
    }
    return result;
  }

  private parseError(responseText: string): unknown {
    try {
      const parsed = JSON.parse(responseText) as { detail?: unknown };
      return parsed.detail ?? {
        code: 'translation_provider_not_ready',
        message: 'Translation is not ready on the AI service.',
      };
    } catch {
      return {
        code: 'translation_provider_not_ready',
        message: 'Translation is not ready on the AI service.',
      };
    }
  }
}
