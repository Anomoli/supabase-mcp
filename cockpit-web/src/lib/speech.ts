export function browserSpeechSupported(): boolean {
  return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
}

type SpeechRecognitionCtor = new () => {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

interface SpeechRecognitionEventLike {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

export function startDictation(opts: {
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
  onEnd?: () => void;
}): { stop: () => void } {
  const Recognition =
    (window as unknown as { SpeechRecognition?: SpeechRecognitionCtor }).SpeechRecognition ||
    (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionCtor }).webkitSpeechRecognition;

  if (!Recognition) {
    opts.onError('Speech recognition is not supported on this browser.');
    return { stop: () => undefined };
  }

  const recognition = new Recognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    const transcript = event.results[0]?.[0]?.transcript?.trim() ?? '';
    if (transcript) opts.onTranscript(transcript);
  };

  recognition.onerror = (event) => {
    opts.onError(`Voice input error: ${event.error}`);
  };

  recognition.onend = () => {
    opts.onEnd?.();
  };

  recognition.start();

  return {
    stop: () => recognition.stop()
  };
}

export function speakText(text: string): void {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'en-US';
  utterance.rate = 1;
  window.speechSynthesis.speak(utterance);
}
