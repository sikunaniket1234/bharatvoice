import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
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
});
