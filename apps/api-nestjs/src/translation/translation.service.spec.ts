import { BadRequestException, ServiceUnavailableException } from '@nestjs/common';
import { TranslationRequestDto } from './translation.dto';
import { TranslationService } from './translation.service';

describe('TranslationService', () => {
  const service = new TranslationService();
  const originalAiServiceUrl = process.env.AI_SERVICE_URL;

  beforeEach(() => {
    process.env.AI_SERVICE_URL = 'http://127.0.0.1:8000';
  });

  afterEach(() => {
    jest.restoreAllMocks();
    if (originalAiServiceUrl === undefined) delete process.env.AI_SERVICE_URL;
    else process.env.AI_SERVICE_URL = originalAiServiceUrl;
  });

  it('rejects Odia-to-Hindi before contacting the AI service', async () => {
    const fetchSpy = jest.spyOn(global, 'fetch');
    const request = {
      text: 'ନମସ୍କାର',
      source_language: 'or',
      target_language: 'hi',
    } as TranslationRequestDto;

    await expect(service.translate(request)).rejects.toBeInstanceOf(BadRequestException);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('preserves the explicit not-ready state from FastAPI', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: 'translation_provider_not_ready',
            message: 'Model not configured',
          },
        }),
        { status: 503, headers: { 'content-type': 'application/json' } },
      ),
    );
    const request = {
      text: 'Hello',
      source_language: 'en',
      target_language: 'or',
    } as TranslationRequestDto;

    try {
      await service.translate(request);
      fail('Expected the unavailable AI provider to be surfaced.');
    } catch (error) {
      expect(error).toBeInstanceOf(ServiceUnavailableException);
      expect((error as ServiceUnavailableException).getStatus()).toBe(503);
    }
  });
});
