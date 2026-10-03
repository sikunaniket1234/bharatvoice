import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

type LanguageCode = 'en' | 'or' | 'hi';
type Tool = 'translate' | 'speech' | 'voice' | 'conversation' | 'transliterate' | 'history';

interface LanguageOption {
  code: LanguageCode;
  name: string;
  nativeName: string;
  locale: string;
}

interface TranslationRecord {
  id: string;
  text: string;
  translatedText: string;
  sourceLanguage: LanguageCode;
  targetLanguage: LanguageCode;
  createdAt: number;
}

interface ConversationMessage {
  id: string;
  text: string;
  translatedText: string;
  sourceLanguage: LanguageCode;
  targetLanguage: LanguageCode;
  pending?: boolean;
  error?: string;
}

interface SpeechRecognitionResultLike extends ArrayLike<{ transcript: string }> {}
interface SpeechRecognitionEventLike extends Event {
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: Event) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

const LANGUAGES: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English', locale: 'en-IN' },
  { code: 'or', name: 'Odia', nativeName: 'ଓଡ଼ିଆ', locale: 'or-IN' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', locale: 'hi-IN' },
];

const SAMPLE_PHRASES: Record<LanguageCode, string[]> = {
  en: ['Where is the railway station?', 'Thank you very much.', 'Please speak slowly.'],
  or: ['ରେଳ ଷ୍ଟେସନ କେଉଁଠାରେ?', 'ଆପଣଙ୍କୁ ବହୁତ ଧନ୍ୟବାଦ।', 'ଦୟାକରି ଧୀରେ କୁହନ୍ତୁ।'],
  hi: ['रेलवे स्टेशन कहाँ है?', 'आपका बहुत धन्यवाद।', 'कृपया धीरे बोलिए।'],
};

/**
 * Languages the microphone is allowed to listen in.
 *
 * Voice input is deliberately limited to English and Odia. Hindi stays
 * selectable for typing and text-to-speech, but the browser speech
 * recognition used here is not offered for it.
 */
const SPEECH_INPUT_LANGUAGES: LanguageCode[] = ['en', 'or'];

const WORD_MAP: Record<string, Record<'or' | 'hi', string>> = {
  namaste: { or: 'ନମସ୍କାର', hi: 'नमस्ते' },
  dhanyabad: { or: 'ଧନ୍ୟବାଦ', hi: 'धन्यवाद' },
  pani: { or: 'ପାଣି', hi: 'पानी' },
  ghar: { or: 'ଘର', hi: 'घर' },
  bharat: { or: 'ଭାରତ', hi: 'भारत' },
  odisha: { or: 'ଓଡ଼ିଶା', hi: 'ओडिशा' },
  bhai: { or: 'ଭାଇ', hi: 'भाई' },
};

@Component({
  selector: 'app-root',
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly http = inject(HttpClient);
  private readonly historyKey = 'bharatvoice.translation-history.v1';

  protected readonly languages = LANGUAGES;
  protected readonly samplePhrases = SAMPLE_PHRASES;
  protected readonly tools: { id: Tool; label: string; icon: string }[] = [
    { id: 'translate', label: 'Translate', icon: '文' },
    { id: 'speech', label: 'Speech to text', icon: '◖' },
    { id: 'voice', label: 'Text to speech', icon: '♫' },
    { id: 'conversation', label: 'Conversation', icon: '↔' },
    { id: 'transliterate', label: 'Transliteration', icon: 'अ' },
    { id: 'history', label: 'History', icon: '◷' },
  ];

  protected activeTool: Tool = 'translate';
  protected sourceLanguage: LanguageCode = 'or';
  protected targetLanguage: LanguageCode = 'en';
  protected sourceText = '';
  protected translatedText = '';
  protected translationStatus = '';
  protected busy = false;
  protected theme: 'light' | 'dark' = 'light';
  protected toastMessage = '';
  protected history: TranslationRecord[] = this.loadHistory();
  protected speechLanguage: LanguageCode = 'or';
protected speechTargetLanguage: LanguageCode = 'en';
  protected speechText = '';
  protected speechListening = false;
  protected voiceLanguage: LanguageCode = 'or';
  protected voiceText = '';
  protected speechRate = 1;
  protected conversationLanguage: LanguageCode = 'or';
  protected conversationDraftA = '';
  protected conversationDraftB = '';
  protected conversationMessages: ConversationMessage[] = [];
  protected romanText = '';
  protected romanTarget: 'or' | 'hi' = 'or';
  protected romanOutput = '';

  private recognition: SpeechRecognitionLike | null = null;
  private toastTimer?: ReturnType<typeof setTimeout>;
  protected listeningTarget: string | null = null;

  /**
   * Keep a chosen pair usable. IndicTrans2 has no direct Odia-Hindi route, so
   * a pair where neither side is English collapses onto English. Same-language
   * pairs are allowed for English and Odia only, because those are the
   * dictation cases (speak Odia, read Odia) which transcription alone handles.
   */
  private static constrainPair(a: LanguageCode, b: LanguageCode): [LanguageCode, LanguageCode] {
    if (a === b) {
      return a === 'hi' ? ['hi', 'en'] : [a, b];
    }
    if (a !== 'en' && b !== 'en') {
      return [a, 'en'];
    }
    return [a, b];
  }

  protected speechInputSupported(code: LanguageCode): boolean {
    return SPEECH_INPUT_LANGUAGES.includes(code);
  }

  protected isListening(target: string): boolean {
    return this.listeningTarget === target;
  }

  protected get sourceLanguageName(): string {
    return this.language(this.sourceLanguage).name;
  }

  protected get targetLanguageName(): string {
    return this.language(this.targetLanguage).name;
  }

  protected get voiceOutputSupported(): boolean {
    return typeof window !== 'undefined' && 'speechSynthesis' in window;
  }

  protected selectTool(tool: Tool): void {
    this.activeTool = tool;
    this.translationStatus = '';
  }

  protected selectPair(source: LanguageCode, target: LanguageCode): void {
    this.sourceLanguage = source;
    this.targetLanguage = target;
    this.sourceText = SAMPLE_PHRASES[source][0];
    this.translatedText = '';
    this.translationStatus = '';
  }

  protected changeSourceLanguage(source: LanguageCode): void {
    [this.sourceLanguage, this.targetLanguage] = App.constrainPair(source, this.targetLanguage);
    this.translatedText = '';
    this.translationStatus = '';
  }

  protected changeTargetLanguage(target: LanguageCode): void {
    [this.sourceLanguage, this.targetLanguage] = App.constrainPair(this.sourceLanguage, target);
    this.translatedText = '';
    this.translationStatus = '';
  }

  protected swapLanguages(): void {
    [this.sourceLanguage, this.targetLanguage] = App.constrainPair(this.targetLanguage, this.sourceLanguage);
    [this.sourceText, this.translatedText] = [this.translatedText, this.sourceText];
    this.translationStatus = '';
  }

  protected translate(): void {
    const text = this.sourceText.trim();
    if (!text) {
      this.translationStatus = 'Add a phrase first, then we can translate it.';
      return;
    }
    const source = this.sourceLanguage;
    const target = this.targetLanguage;
    if (source === target) {
      // Dictation case: English to English, Odia to Odia. en:en and or:or are
      // not valid IndicTrans2 pairs, and sending already-correct text through
      // the model could only rewrite it, so transcription stands alone.
      this.completeTranslation(text, text, source, target,
        'Heard in ' + this.language(source).name + '. No translation was needed.');
      return;
    }
    this.requestTranslation(text, source, target, (result) => {
      this.completeTranslation(text, result.translated_text, source, target, 'Translation complete.');
    });
  }

  private completeTranslation(
    text: string,
    translated: string,
    source: LanguageCode,
    target: LanguageCode,
    status: string,
  ): void {
    this.translatedText = translated;
    this.translationStatus = status;
    this.history = [
      {
        id: crypto.randomUUID(),
        text,
        translatedText: translated,
        sourceLanguage: source,
        targetLanguage: target,
        createdAt: Date.now(),
      },
      ...this.history,
    ].slice(0, 30);
    this.saveHistory();
  }

  protected useHistory(record: TranslationRecord): void {
    this.sourceLanguage = record.sourceLanguage;
    this.targetLanguage = record.targetLanguage;
    this.sourceText = record.text;
    this.translatedText = record.translatedText;
    this.translationStatus = '';
    this.activeTool = 'translate';
  }

  protected deleteHistory(id: string): void {
    this.history = this.history.filter((record) => record.id !== id);
    this.saveHistory();
  }

  protected clearHistory(): void {
    this.history = [];
    this.saveHistory();
  }

  protected async copyText(text: string): Promise<void> {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      this.showToast('Copied to clipboard');
    } catch {
      this.showToast('Clipboard access is unavailable in this browser.');
    }
  }

  protected speak(text: string, language: LanguageCode): void {
    if (!text.trim() || !this.voiceOutputSupported) {
      this.showToast('Speech playback is not available in this browser.');
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = this.language(language).locale;
    utterance.rate = this.speechRate;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  protected stopSpeaking(): void {
    if (this.voiceOutputSupported) window.speechSynthesis.cancel();
  }

  protected toggleListening(target: 'speech' | 'conversation-a' | 'conversation-b' | 'translate'): void {
    if (this.recognition) {
      this.recognition.stop();
      return;
    }
    const speechWindow = window as Window & {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const SpeechRecognitionCtor = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      this.showToast('Voice input is not supported by this browser.');
      return;
    }
    const code = target === 'speech' ? this.speechLanguage : target === 'translate' ? this.sourceLanguage : target === 'conversation-a' ? 'en' : this.conversationLanguage;
    if (!this.speechInputSupported(code)) {
      this.showToast('Voice input works in English and Odia only. ' + this.language(code).name + ' is not available for the microphone yet.');
      return;
    }
    const recognition = new SpeechRecognitionCtor();
    recognition.lang = this.language(code).locale;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? '';
      if (target === 'speech') this.speechText = transcript;
      else if (target === 'translate') this.sourceText = transcript;
      else if (target === 'conversation-a') this.conversationDraftA = transcript;
      else this.conversationDraftB = transcript;
    };
    recognition.onerror = () => this.showToast('Could not hear you. Check microphone permission and try again.');
    recognition.onend = () => {
      this.recognition = null;
      this.listeningTarget = null;
      this.speechListening = false;
    };
    this.recognition = recognition;
    this.listeningTarget = target;
    this.speechListening = true;
    try {
      recognition.start();
    } catch {
      this.recognition = null;
      this.listeningTarget = null;
      this.speechListening = false;
      this.showToast('Voice input could not start.');
    }
  }

  protected translateSpeech(): void {
    const text = this.speechText.trim();
    if (!text) {
      this.showToast('Record or type a phrase first.');
      return;
    }
    const [source, target] = App.constrainPair(this.speechLanguage, this.speechTargetLanguage);
    this.speechTargetLanguage = target;
    this.sourceLanguage = source;
    this.targetLanguage = target;
    this.sourceText = text;
    this.activeTool = 'translate';
    this.translate();
  }

  protected sendConversation(speaker: 'a' | 'b'): void {
    const text = (speaker === 'a' ? this.conversationDraftA : this.conversationDraftB).trim();
    const sourceLanguage: LanguageCode = speaker === 'a' ? 'en' : this.conversationLanguage;
    const targetLanguage: LanguageCode = sourceLanguage === 'en' ? this.conversationLanguage : 'en';
    if (!text) return;
    if (speaker === 'a') this.conversationDraftA = '';
    else this.conversationDraftB = '';
    const message: ConversationMessage = {
      id: crypto.randomUUID(),
      text,
      translatedText: '',
      sourceLanguage,
      targetLanguage,
      pending: true,
    };
    this.conversationMessages = [...this.conversationMessages, message];
    if (sourceLanguage === targetLanguage) {
      // Both speakers picked the same language, so this turn is transcription
      // only. en:en is not a valid IndicTrans2 pair and must not be sent.
      this.updateConversation(message.id, { translatedText: text, pending: false });
      return;
    }
    this.requestTranslation(text, sourceLanguage, targetLanguage, (result) => {
      this.updateConversation(message.id, {
        translatedText: result.translated_text,
        pending: false,
      });
    }, (error) => {
      this.updateConversation(message.id, { pending: false, error });
    });
  }

  protected updateTransliteration(): void {
    this.romanOutput = this.romanText
      .split(/(\s+)/)
      .map((token) => {
        if (/^\s+$/.test(token)) return token;
        const match = token.match(/^([a-zA-Z]+)(.*)$/);
        if (!match) return token;
        const replacement = WORD_MAP[match[1].toLowerCase()]?.[this.romanTarget];
        return replacement ? replacement + match[2] : token;
      })
      .join('');
  }

  protected language(code: LanguageCode): LanguageOption {
    return LANGUAGES.find((language) => language.code === code) ?? LANGUAGES[0];
  }

  protected toggleTheme(): void {
    this.theme = this.theme === 'light' ? 'dark' : 'light';
    document.documentElement.dataset['theme'] = this.theme;
  }

  protected formatTime(timestamp: number): string {
    return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(timestamp);
  }

  protected trackById(_index: number, record: { id: string }): string {
    return record.id;
  }

  private requestTranslation(
    text: string,
    sourceLanguage: LanguageCode,
    targetLanguage: LanguageCode,
    onSuccess: (response: { translated_text: string }) => void,
    onError?: (message: string) => void,
  ): void {
    this.busy = true;
    this.translationStatus = 'Connecting to the BharatVoice translation service…';
    this.http.post<{ translated_text: string }>('/api/v1/translation', {
      text,
      source_language: sourceLanguage,
      target_language: targetLanguage,
    }).subscribe({
      next: (response) => {
        this.busy = false;
        onSuccess(response);
      },
      error: (error: HttpErrorResponse) => {
        this.busy = false;
        const message = this.errorMessage(error);
        this.translationStatus = message;
        if (onError) onError(message);
      },
    });
  }

  private errorMessage(error: HttpErrorResponse): string {
    const detail = error.error?.detail;
    if (typeof detail?.message === 'string') return detail.message;
    if (error.status === 0) return 'The local API is unreachable. Check that the Docker services are running.';
    if (error.status === 503) return 'Translation is not ready yet. The IndicTrans2 model will be connected on the desktop.';
    if (error.status === 400 || error.status === 422) return 'That language pair or phrase is not supported.';
    return 'Something went wrong while translating. Please try again.';
  }

  private updateConversation(id: string, changes: Partial<ConversationMessage>): void {
    this.conversationMessages = this.conversationMessages.map((message) =>
      message.id === id ? { ...message, ...changes } : message,
    );
  }

  private loadHistory(): TranslationRecord[] {
    try {
      const value = localStorage.getItem(this.historyKey);
      return value ? (JSON.parse(value) as TranslationRecord[]) : [];
    } catch {
      return [];
    }
  }

  private saveHistory(): void {
    try {
      localStorage.setItem(this.historyKey, JSON.stringify(this.history));
    } catch {
      this.showToast('Could not save history on this device.');
    }
  }

  private showToast(message: string): void {
    this.toastMessage = message;
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => (this.toastMessage = ''), 2800);
  }
}
