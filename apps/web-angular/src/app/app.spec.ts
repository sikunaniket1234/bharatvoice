import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render the BharatVoice translator', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Every voice');
    expect(compiled.querySelector('[aria-label="Text translation"]')).toBeTruthy();
  });

  it('does not allow a direct Odia-to-Hindi pair', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance as unknown as {
      changeSourceLanguage: (code: 'en' | 'or' | 'hi') => void;
      sourceLanguage: string;
      targetLanguage: string;
    };

    app.changeSourceLanguage('hi');

    expect(app.sourceLanguage).toBe('hi');
    expect(app.targetLanguage).toBe('en');
  });

  describe('speech-to-text language coverage', () => {
    type AppUnderTest = {
      changeSourceLanguage: (code: 'en' | 'or' | 'hi') => void;
      changeTargetLanguage: (code: 'en' | 'or' | 'hi') => void;
      sourceLanguage: string;
      targetLanguage: string;
      speechInputSupported: (code: 'en' | 'or' | 'hi') => boolean;
    };

    function makeApp(): AppUnderTest {
      const fixture = TestBed.createComponent(App);
      return fixture.componentInstance as unknown as AppUnderTest;
    }

    it('allows all four English and Odia dictation pairs', () => {
      const app = makeApp();

      for (const [source, target] of [
        ['or', 'en'],
        ['or', 'or'],
        ['en', 'en'],
        ['en', 'or'],
      ] as const) {
        app.changeSourceLanguage(source);
        app.changeTargetLanguage(target);

        expect({ source: app.sourceLanguage, target: app.targetLanguage }).toEqual({
          source,
          target,
        });
      }
    });

    it('offers the microphone in English and Odia but not Hindi', () => {
      const app = makeApp();

      expect(app.speechInputSupported('en')).toBe(true);
      expect(app.speechInputSupported('or')).toBe(true);
      expect(app.speechInputSupported('hi')).toBe(false);
    });

    it('still refuses a Hindi-to-Hindi pair', () => {
      const app = makeApp();

      app.changeSourceLanguage('hi');
      app.changeTargetLanguage('hi');

      expect(app.sourceLanguage).toBe('hi');
      expect(app.targetLanguage).toBe('en');
    });
  });

  it('does not call the API for a same-language pair', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance as unknown as {
      changeSourceLanguage: (code: 'en' | 'or' | 'hi') => void;
      changeTargetLanguage: (code: 'en' | 'or' | 'hi') => void;
      sourceText: string;
      translatedText: string;
      translationStatus: string;
      translate: () => void;
      history: unknown[];
    };
    const http = TestBed.inject(HttpTestingController);

    app.changeSourceLanguage('or');
    app.changeTargetLanguage('or');
    app.sourceText = 'ଆଜି ବରଷା ଭଲ ଲାଗିଲା।';
    app.translate();

    // en:en and or:or are not valid IndicTrans2 pairs, so nothing may be sent.
    http.expectNone('/api/v1/translation');
    expect(app.translatedText).toBe('ଆଜି ବରଷା ଭଲ ଲାଗିଲା।');
    expect(app.translationStatus).toContain('No translation was needed');
    http.verify();
  });
});
